FROM node:22-alpine
WORKDIR /app
COPY server.js ./
COPY public ./public
ENV NODE_ENV=production PORT=3000 DATA_DIR=/app/data
# Le dossier appartient à node : le volume nommé hérite de ces droits à sa création.
RUN mkdir -p /app/data && chown node:node /app/data
VOLUME ["/app/data"]
EXPOSE 3000
USER node
CMD ["node", "server.js"]
