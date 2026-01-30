# Eventstream Deployment Guide

## Overview
This guide explains how to deploy and configure the Fabric Eventstream for real-time IoT telemetry ingestion.

## Prerequisites
- Microsoft Fabric workspace with Eventstream capability
- Azure Event Hub namespace with IoT telemetry stream
- KQL Database deployed and configured
- Appropriate permissions (Contributor or Admin)

## Deployment Steps

### 1. Create Eventstream in Fabric

```bash
# Using Fabric REST API
POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/eventstreams
```

Or via the Fabric Portal:
1. Navigate to your Fabric workspace
2. Click "New" → "Eventstream"
3. Name: `IoT-Telemetry-Eventstream`

### 2. Configure Source

Add Azure Event Hub as source:
- **Connection**: Use managed identity or connection string
- **Event Hub Namespace**: Your Event Hub namespace name
- **Event Hub Name**: `iot-telemetry-stream`
- **Consumer Group**: `$Default` or create dedicated group
- **Data Format**: JSON
- **Timestamp Column**: `eventTime`

### 3. Add Transformations

#### Transform 1: Parse and Enrich
```sql
-- Add derived fields
SELECT
    *,
    System.Timestamp() AS ingestionTime,
    CASE
        WHEN temperature > 85 OR temperature < 0 THEN true
        WHEN voltage > 280 OR voltage < 180 THEN true
        ELSE false
    END AS isAnomaly,
    CASE
        WHEN location IN ('Seattle', 'New York') THEN 'North America'
        WHEN location = 'London' THEN 'Europe'
        WHEN location = 'Tokyo' THEN 'Asia'
        WHEN location = 'Sydney' THEN 'Oceania'
        ELSE 'Unknown'
    END AS region
FROM EventHubSource
```

#### Transform 2: Filter Valid Records
```sql
SELECT *
FROM EnrichedStream
WHERE deviceId IS NOT NULL
  AND eventTime IS NOT NULL
```

#### Transform 3: Aggregate Metrics (5-minute windows)
```sql
SELECT
    System.Timestamp() AS windowStart,
    deviceId,
    deviceType,
    location,
    AVG(temperature) AS avgTemperature,
    MAX(temperature) AS maxTemperature,
    MIN(temperature) AS minTemperature,
    AVG(humidity) AS avgHumidity,
    SUM(energyConsumed) AS totalEnergy,
    COUNT(*) AS eventCount
FROM ValidRecords
GROUP BY
    TumblingWindow(minute, 5),
    deviceId,
    deviceType,
    location
```

### 4. Configure Destinations

#### Destination 1: KQL Database (Raw Data)
- **Destination Type**: KQL Database
- **Database**: Select your KQL database
- **Table**: `IoTTelemetry`
- **Mapping**: `IoTTelemetryMapping`
- **Input Format**: JSON

#### Destination 2: KQL Database (Aggregates)
- **Destination Type**: KQL Database
- **Database**: Select your KQL database
- **Table**: `AggregatedMetrics`
- **Mapping**: `AggregatedMetricsMapping`
- **Input Format**: JSON

#### Destination 3: Lakehouse (Historical)
- **Destination Type**: Lakehouse
- **Lakehouse**: Your lakehouse name
- **Table**: `iot_telemetry_raw`
- **Mode**: Append

#### Destination 4: Alert Event Hub
- **Destination Type**: Event Hub
- **Event Hub**: `iot-alerts`
- **Filter**: Only anomalies (isAnomaly = true)

### 5. Enable Error Handling

Configure dead-letter queue:
- **DLQ Event Hub**: `iot-dlq`
- **Max Retries**: 3
- **Backoff Policy**: Exponential

### 6. Set Up Monitoring

Enable diagnostics:
```bash
# Azure Monitor Diagnostic Settings
az monitor diagnostic-settings create \
  --resource <eventstream-resource-id> \
  --name "eventstream-diagnostics" \
  --logs '[{"category": "OperationalLogs", "enabled": true}]' \
  --metrics '[{"category": "AllMetrics", "enabled": true}]' \
  --workspace <log-analytics-workspace-id>
```

Create alert rules:
- High error rate (> 5%)
- Low throughput (< 0.1 MB/s for 5 minutes)
- Processing lag (> 60 seconds)

## Testing

### Test Data Flow

1. Send test event to Event Hub:
```bash
python simulators/iot_simulator.py --devices 1 --duration 10
```

2. Verify data in KQL Database:
```kql
IoTTelemetry
| where EventTime > ago(5m)
| count
```

3. Check aggregations:
```kql
AggregatedMetrics
| where WindowStart > ago(10m)
| count
```

### Validate Transformations

```kql
// Check enrichment fields
IoTTelemetry
| where EventTime > ago(5m)
| project DeviceId, EventTime, Temperature, IsAnomaly
| take 10

// Verify aggregation accuracy
let raw = IoTTelemetry
    | where EventTime > ago(1h)
    | summarize CalculatedAvg = avg(Temperature) by bin(EventTime, 5m), DeviceId;
let agg = AggregatedMetrics
    | where WindowStart > ago(1h)
    | project WindowStart, DeviceId, StoredAvg = AvgTemperature;
raw
| join kind=inner (agg) on $left.EventTime == $right.WindowStart and $left.DeviceId == $right.DeviceId
| project EventTime, DeviceId, CalculatedAvg, StoredAvg, Difference = abs(CalculatedAvg - StoredAvg)
| where Difference > 0.1
```

## Performance Tuning

### Partition Strategy
- Use `deviceId` as partition key for Event Hub
- Configure 4-8 partitions for moderate load (10-100 devices)
- Scale to 16-32 partitions for high load (1000+ devices)

### Throughput Units
- Standard tier: Start with 1 TU, enable auto-inflate
- Premium tier: Start with 1 PU for production workloads

### Batch Configuration
```json
{
  "batchSize": 100,
  "batchTimeoutSeconds": 10,
  "maxConcurrentBatches": 5
}
```

### KQL Ingestion Optimization
- Enable streaming ingestion for near real-time latency
- Use batching policy for cost optimization:
```kql
.alter table IoTTelemetry policy ingestionbatching
```
{
  "MaximumBatchingTimeSpan": "00:00:30",
  "MaximumNumberOfItems": 500,
  "MaximumRawDataSizeMB": 1024
}
```
```

## Troubleshooting

### Common Issues

#### 1. Data Not Flowing
- Check Event Hub permissions (managed identity needs "Azure Event Hubs Data Receiver" role)
- Verify consumer group exists
- Check Eventstream status in Fabric portal

#### 2. Schema Mismatches
- Verify KQL table schema matches data format
- Check ingestion mapping is correct
- Review error logs in diagnostic settings

#### 3. High Latency
- Check Event Hub lag metrics
- Verify KQL cluster is not throttled
- Review transformation complexity

#### 4. Missing Data
- Check for events in dead-letter queue
- Review error rates in metrics
- Verify time range in queries (check UTC vs local time)

### Diagnostic Queries

```kql
// Check ingestion statistics
.show ingestion failures
| where FailedOn > ago(1h)
| summarize count() by FailureKind

// Monitor ingestion latency
.show ingestion latency table IoTTelemetry
| summarize avg(IngestionLatency) by bin(Timestamp, 5m)

// Check for data gaps
IoTTelemetry
| make-series count() on EventTime step 1m
| render timechart
```

## Maintenance

### Regular Tasks
- Monitor throughput and latency metrics
- Review error rates weekly
- Update transformation logic as schema evolves
- Archive old data to cold storage (Azure Data Lake)
- Test failover scenarios quarterly

### Scaling Guidelines
| Devices | Events/sec | Event Hub | KQL Cluster | Recommended Setup |
|---------|-----------|-----------|-------------|-------------------|
| 1-100 | < 100 | Standard (1 TU) | Dev SKU | Dev/Test |
| 100-1000 | 100-1000 | Standard (5 TU) | Standard D11 v2 | Small Production |
| 1000-10000 | 1000-10000 | Premium (1 PU) | Standard D13 v2 | Medium Production |
| 10000+ | > 10000 | Premium (2+ PU) | Standard D14 v2+ | Large Production |

## References
- [Microsoft Fabric Eventstream Documentation](https://learn.microsoft.com/fabric/eventstream/)
- [Azure Event Hubs Best Practices](https://learn.microsoft.com/azure/event-hubs/)
- [KQL Ingestion Overview](https://learn.microsoft.com/azure/data-explorer/ingest-data-overview)
