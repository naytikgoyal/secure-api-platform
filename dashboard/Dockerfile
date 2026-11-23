FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# Points the dashboard's browser-side fetch() calls at the Gateway/Auth
# Server. Overridden at build/run time if your ports differ (see docker-compose.yml).
ENV VITE_GATEWAY_URL=https://localhost:3000
ENV VITE_AUTH_URL=https://localhost:4000

EXPOSE 5173
CMD ["npm", "run", "dev"]
