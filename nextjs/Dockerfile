# Development stage
FROM node:20-alpine AS development

WORKDIR /app

# Install dependencies will happen at runtime
EXPOSE 3000

# Create startup script
RUN echo '#!/bin/sh' > /start.sh && \
    echo 'cd /app' >> /start.sh && \
    echo 'if [ ! -d "node_modules" ] || [ ! -f "node_modules/.installed" ]; then' >> /start.sh && \
    echo '  echo "Installing dependencies..."' >> /start.sh && \
    echo '  npm install' >> /start.sh && \
    echo '  touch node_modules/.installed' >> /start.sh && \
    echo 'fi' >> /start.sh && \
    echo 'echo "Starting development server..."' >> /start.sh && \
    echo 'exec npm run dev' >> /start.sh && \
    chmod +x /start.sh

CMD ["/start.sh"]

# Production build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy all files
COPY . .

# Build the application
RUN npm run build

# Production runtime stage
FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

# Copy necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
