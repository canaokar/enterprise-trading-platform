#!/usr/bin/env bash
set -euo pipefail

broker="${KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}"
tool=/opt/kafka/bin/kafka-topics.sh

create_topic() {
  "$tool" --bootstrap-server "$broker" --create --if-not-exists \
    --topic "$1" --partitions "$2" --replication-factor 1 \
    --config "retention.ms=$3"
}

create_topic orders 3 604800000
create_topic orders.DLT 3 604800000
create_topic trade-events 3 2592000000
create_topic trade-events.DLT 3 2592000000
create_topic market-data 6 86400000
create_topic market-data.DLT 6 86400000
