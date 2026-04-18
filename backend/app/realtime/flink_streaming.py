import json
from pyflink.common import WatermarkStrategy, Time, Configuration
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment, KeyedProcessFunction, RuntimeContext
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaSink, DeliveryGuarantee, KafkaRecordSerializationSchema
from pyflink.datastream.state import ValueStateDescriptor, MapStateDescriptor
from pyflink.common.typeinfo import Types

# LATENCY TARGET: <10ms for metrics computation
# SYSTEM TARGET: Sub-90ms end-to-end fraud scoring

class IdentityResolutionFunction(KeyedProcessFunction):
    """
    KeyedProcessFunction to manage Global Synthetic Identity.
    Maps disparate device IDs and IPs to a single stateful entity.
    """
    def __init__(self):
        self.device_state = None
        self.last_seen = None

    def open(self, runtime_context: RuntimeContext):
        # State to track unique devices per User ID over 24h
        self.device_state = runtime_context.get_map_state(
            MapStateDescriptor("devices", Types.STRING(), Types.LONG())
        )
        self.last_seen = runtime_context.get_value_state(
            ValueStateDescriptor("last_seen", Types.LONG())
        )

    def process_element(self, value, ctx: KeyedProcessFunction.Context):
        data = json.loads(value)
        user_id = data.get("user_id")
        device_id = data.get("device_id")
        current_time = ctx.timer_service().current_processing_time()

        # Update device registry
        self.device_state.put(device_id, current_time)
        self.last_seen.update(current_time)

        # 8-Check Gate Prep: Multiplicity Check
        # Count unique devices in the last 24 hours
        unique_devices = 0
        cutoff = current_time - (24 * 60 * 60 * 1000)
        
        # Cleanup and count
        devices_to_remove = []
        for d, ts in self.device_state.items():
            if ts < cutoff:
                devices_to_remove.append(d)
            else:
                unique_devices += 1
        
        for d in devices_to_remove:
            self.device_state.remove(d)

        data["unique_devices_24h"] = unique_devices
        data["synthetic_identity_id"] = f"SYN-{hash(user_id)}" # Global Synthetic Identity
        
        yield json.dumps(data)

class WindowedMetricsFunction(KeyedProcessFunction):
    """
    Calculates Velocity and Frequency in-memory.
    Optimization: Avoids external DB hits to maintain <10ms windowed latency.
    """
    def __init__(self):
        self.tx_history = None

    def open(self, runtime_context: RuntimeContext):
        # Store timestamp and amount for windowed calculations
        self.tx_history = runtime_context.get_map_state(
            MapStateDescriptor("tx_history", Types.LONG(), Types.FLOAT())
        )

    def process_element(self, value, ctx: KeyedProcessFunction.Context):
        data = json.loads(value)
        current_time = ctx.timer_service().current_processing_time()
        amount = float(data.get("amount", 0))

        self.tx_history.put(current_time, amount)

        # 1. VELOCITY: Transactions in last 5 minutes
        v_cutoff = current_time - (5 * 60 * 1000)
        velocity_count = 0
        velocity_sum = 0.0
        
        # 2. FREQUENCY: 1-hour rolling metrics
        f_cutoff = current_time - (60 * 60 * 1000)
        
        history_to_remove = []
        for ts, val in self.tx_history.items():
            if ts < f_cutoff:
                history_to_remove.append(ts)
            else:
                if ts >= v_cutoff:
                    velocity_count += 1
                    velocity_sum += val

        for ts in history_to_remove:
            self.tx_history.remove(ts)

        data["velocity_5m_count"] = velocity_count
        data["velocity_5m_sum"] = velocity_sum
        
        # Parallel Execution Hint:
        # GNN and Anomaly workers consume 'enriched_transactions' topic in parallel
        # to ensure sub-90ms scoring.
        yield json.dumps(data)

def run_finguard_stream():
    """
    FinGuard AI 2.0 Streaming Backbone.
    Replaces polling-based ingestion with an event-driven Kafka-Flink pipeline.
    """
    config = Configuration()
    env = StreamExecutionEnvironment.get_execution_environment(config)
    
    # Source: raw_transactions
    kafka_source = KafkaSource.builder() \
        .set_bootstrap_servers("kafka:9092") \
        .set_topics("raw_transactions") \
        .set_group_id("finguard-streaming-group") \
        .set_value_only_deserializer(SimpleStringSchema()) \
        .build()

    stream = env.from_source(kafka_source, WatermarkStrategy.no_watermarks(), "Kafka Source")

    # Pipeline Flow
    processed_stream = stream \
        .key_by(lambda x: json.loads(x).get("user_id")) \
        .process(IdentityResolutionFunction()) \
        .key_by(lambda x: json.loads(x).get("user_id")) \
        .process(WindowedMetricsFunction())

    # Sink: enriched_transactions (Consumed by parallel ML workers)
    kafka_sink = KafkaSink.builder() \
        .set_bootstrap_servers("kafka:9092") \
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
                .set_topic("enriched_transactions")
                .set_value_serialization_schema(SimpleStringSchema())
                .build()
        ) \
        .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE) \
        .build()

    processed_stream.sink_to(kafka_sink)

    env.execute("FinGuard AI 2.0 Streaming Engine")

if __name__ == "__main__":
    run_finguard_stream()
