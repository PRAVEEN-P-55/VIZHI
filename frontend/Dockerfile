FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM nginx:1.27-alpine
# Install gettext for envsubst (replaces $BACKEND_URL in nginx.conf at startup)
RUN apk add --no-cache gettext
# Store as template; entrypoint will run envsubst before nginx starts
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
# BACKEND_URL default works for local docker-compose; override on Render.
ENV BACKEND_URL=http://localhost:8000
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
