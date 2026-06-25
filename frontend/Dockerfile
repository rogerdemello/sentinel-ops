# SentinelOps frontend — build with Vite, serve via nginx
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Optional absolute API base baked into the SPA at build time. Leave empty to use
# same-origin relative requests (nginx proxies /api + /ws to BACKEND_ORIGIN).
ARG VITE_API_BASE=""
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:alpine
# The official nginx image runs envsubst on /etc/nginx/templates/*.template at
# startup, writing results to /etc/nginx/conf.d/. NGINX_ENVSUBST_FILTER restricts
# substitution to ONLY ${BACKEND_ORIGIN}, so literal nginx vars ($host, $uri,
# $http_upgrade, …) are always preserved regardless of the container environment.
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d
ENV NGINX_ENVSUBST_FILTER=BACKEND_ORIGIN
ENV BACKEND_ORIGIN=http://backend:8000
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
