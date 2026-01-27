# Development stage
FROM node:20-alpine AS development

# Set timezone to IST
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Kolkata /etc/localtime && \
    echo "Asia/Kolkata" > /etc/timezone

ENV TZ=Asia/Kolkata

WORKDIR /app

# Install dependencies will happen at runtime
EXPOSE 3000 5555

# Create startup script
RUN echo '#!/bin/sh' > /start.sh && \
    echo 'cd /app' >> /start.sh && \
    echo 'if [ ! -d "node_modules" ] || [ ! -f "node_modules/.installed" ]; then' >> /start.sh && \
    echo '  echo "Installing dependencies..."' >> /start.sh && \
    echo '  npm install' >> /start.sh && \
    echo '  touch node_modules/.installed' >> /start.sh && \
    echo 'fi' >> /start.sh && \
    echo 'echo "Generating Prisma Client..."' >> /start.sh && \
    echo 'npx prisma generate' >> /start.sh && \
    echo 'echo "Starting Prisma Studio..."' >> /start.sh && \
    echo 'npm run studio &' >> /start.sh && \
    echo 'echo "Starting development server..."' >> /start.sh && \
    echo 'exec npm run dev' >> /start.sh && \
    chmod +x /start.sh

CMD ["/start.sh"]

# Production build stage
FROM node:20-alpine AS builder

# Set timezone to IST
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Kolkata /etc/localtime && \
    echo "Asia/Kolkata" > /etc/timezone

ENV TZ=Asia/Kolkata

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

# Set timezone to IST
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Kolkata /etc/localtime && \
    echo "Asia/Kolkata" > /etc/timezone

ENV TZ=Asia/Kolkata

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
