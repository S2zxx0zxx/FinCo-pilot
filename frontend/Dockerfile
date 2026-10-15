FROM node:22-slim AS build

WORKDIR /app

ARG VITE_APP_VERSION
ENV VITE_APP_VERSION=$VITE_APP_VERSION
ARG VITE_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG VITE_RAZORPAY_KEY_ID
ARG VITE_SENTRY_ENABLED=false
ARG VITE_SENTRY_DSN
ARG VITE_WEB_VITALS_ENABLED=false
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV VITE_RAZORPAY_KEY_ID=$VITE_RAZORPAY_KEY_ID
ENV VITE_SENTRY_ENABLED=$VITE_SENTRY_ENABLED
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN
ENV VITE_WEB_VITALS_ENABLED=$VITE_WEB_VITALS_ENABLED

COPY package.json package-lock.json .npmrc ./
RUN npm ci

COPY . .
RUN npm run build

# Serve with nginx
FROM nginxinc/nginx-unprivileged:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY security-headers.conf /etc/nginx/finco-security-headers.conf
COPY --from=build /app/node_modules/.cache/finco-security/csp-map.conf.template /etc/nginx/templates/00-finco-csp.conf.template

# Have the image derive the DNS resolver from /etc/resolv.conf, so the same
# image proxies to the backend on Docker, Podman, Kubernetes and Railway with
# no per-platform configuration. 19-resolver.envsh turns that into
# NGINX_RESOLVER (with a Docker fallback) for the config template; setting
# NGINX_RESOLVER explicitly still overrides both.
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1
ENV FINCO_TRUSTED_TYPES_REPORT_ONLY=false
ENV FINCO_STRICT_CSP_MODE=compatibility
COPY --chmod=755 docker-entrypoint.d/19-resolver.envsh /docker-entrypoint.d/

EXPOSE 8080
