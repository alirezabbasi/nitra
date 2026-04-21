FROM rust:1.87-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y pkg-config libssl-dev ca-certificates && rm -rf /var/lib/apt/lists/*
CMD ["sleep", "infinity"]
