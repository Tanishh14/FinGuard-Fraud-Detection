import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ReportParams {
    time_range: '24h' | '7d' | 'monthly' | 'yearly';
    username?: string;
}

/**
 * Downloads a PDF transaction report from the backend.
 */
export const exportTransactionPDF = async (params: ReportParams, token: string | null) => {
    const response = await axios.get(`${BASE_URL}/analytics/reports/download`, {
        params,
        headers: {
            Authorization: `Bearer ${token}`,
        },
        responseType: 'blob',
    });

    // Create link and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `finguard_report_${params.time_range}.pdf`);
    document.body.appendChild(link);
    link.click();

    // Cleanup
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
};
