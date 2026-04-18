# FinGuard AI 2.0 - Frontend
FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy code
COPY . .

# Exposure
EXPOSE 3000

# Start Vite dev server for demo transparency
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
