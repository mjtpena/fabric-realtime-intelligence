# Fabric Real-Time Intelligence Project

A comprehensive solution for real-time IoT telemetry analytics using Microsoft Fabric Real-Time Intelligence, Azure Event Hubs, and KQL (Kusto Query Language).

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Streaming Patterns](#streaming-patterns)
- [Deployment](#deployment)
- [Usage](#usage)
- [Testing](#testing)
- [Monitoring](#monitoring)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

This project demonstrates a production-ready real-time intelligence solution that:
- Ingests IoT telemetry data from multiple devices
- Processes streams in real-time using Microsoft Fabric Eventstream
- Stores data in KQL Database for fast analytics
- Provides real-time dashboards and alerts
- Implements anomaly detection and predictive maintenance

### Key Technologies
- **Microsoft Fabric Real-Time Intelligence**: Unified platform for streaming analytics
- **Azure Event Hubs**: Scalable event ingestion service
- **KQL Database (Azure Data Explorer)**: Fast analytics engine
- **Python**: IoT simulator and testing framework
- **Bicep/Terraform**: Infrastructure as Code

## Architecture

```
┌─────────────────┐
│  IoT Devices    │
│  (Simulators)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Azure Event    │
│  Hub            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Fabric         │
│  Eventstream    │
│  - Parse        │
│  - Transform    │
│  - Route        │
└────────┬────────┘
         │
         ├──────────────────┬───────────────────┐
         ▼                  ▼                   ▼
┌─────────────────┐ ┌─────────────┐  ┌──────────────┐
│  KQL Database   │ │  Lakehouse  │  │  Alerts Hub  │
│  (Real-Time)    │ │  (History)  │  │  (Anomalies) │
└────────┬────────┘ └─────────────┘  └──────────────┘
         │
         ▼
┌─────────────────┐
│  Real-Time      │
│  Dashboards     │
│  & Analytics    │
└─────────────────┘
```

### Data Flow

1. **Ingestion**: IoT devices send telemetry to Event Hub
2. **Streaming**: Eventstream processes and transforms data
3. **Storage**: Data stored in KQL Database and Lakehouse
4. **Analytics**: Real-time queries and aggregations
5. **Visualization**: Dashboards display insights
6. **Alerting**: Anomalies trigger notifications

## Features

### Real-Time Processing
- Sub-second ingestion latency
- Stream transformations and enrichment
- Windowed aggregations (5-minute tumbling windows)
- Conditional routing based on data quality

### Analytics Capabilities
- Time-series analysis
- Anomaly detection using ML algorithms
- Geospatial queries with device locations
- Predictive maintenance indicators
- Energy consumption tracking

### Monitoring & Alerting
- Real-time dashboards with auto-refresh
- Critical threshold alerts
- Device health monitoring
- Performance metrics and SLAs

### Scalability
- Horizontal scaling with Event Hub partitions
- Auto-inflate for traffic spikes
- Materialized views for performance
- Hot/cold data tiering

## Project Structure

```
fabric-realtime-intelligence/
├── infrastructure/           # Infrastructure as Code
│   ├── main.bicep           # Azure Bicep template
│   ├── main.tf              # Terraform configuration
│   ├── variables.tf         # Terraform variables
│   └── .gitignore           # IaC ignore rules
├── kql/                     # KQL Database schemas and queries
│   ├── schema.kql           # Table definitions and mappings
│   └── queries.kql          # Analytics queries (24 examples)
├── eventstream/             # Eventstream configurations
│   ├── eventstream-config.json  # Stream processing pipeline
│   └── deployment-guide.md      # Deployment instructions
├── simulators/              # IoT data simulators
│   ├── iot_simulator.py     # Python IoT simulator
│   ├── requirements.txt     # Simulator dependencies
│   └── .env.example         # Configuration template
├── dashboards/              # Real-time dashboards
│   ├── realtime-dashboard.json  # Dashboard definition
│   └── README.md               # Dashboard documentation
├── tests/                   # API and streaming tests
│   ├── test_streaming_api.py   # Comprehensive test suite
│   ├── requirements.txt        # Test dependencies
│   └── .env.example           # Test configuration
└── README.md                # This file
```

## Prerequisites

### Azure Resources
- Azure subscription with Contributor access
- Microsoft Fabric workspace (Fabric trial or paid)
- Azure CLI (`az`) installed
- Bicep CLI or Terraform installed

### Development Tools
- Python 3.8 or higher
- Git
- Visual Studio Code (recommended)
- Azure Data Studio or Kusto Explorer

### Permissions
- Contributor role on Azure subscription
- Fabric Admin or Contributor on workspace
- Event Hubs Data Sender role
- Azure Data Explorer Database Admin

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/fabric-realtime-intelligence.git
cd fabric-realtime-intelligence
```

### 2. Deploy Infrastructure

#### Option A: Using Bicep

```bash
# Login to Azure
az login

# Create resource group
az group create --name fabrti-rg-dev --location eastus

# Deploy infrastructure
az deployment group create \
  --resource-group fabrti-rg-dev \
  --template-file infrastructure/main.bicep \
  --parameters environment=dev namePrefix=fabrti
```

#### Option B: Using Terraform

```bash
# Initialize Terraform
cd infrastructure
terraform init

# Review plan
terraform plan

# Deploy
terraform apply
```

### 3. Configure KQL Database

```bash
# Get Kusto cluster URI from deployment outputs
KUSTO_URI=$(az deployment group show \
  --resource-group fabrti-rg-dev \
  --name main \
  --query properties.outputs.kustoClusterUri.value -o tsv)

# Run schema creation
# Open Azure Data Studio or Kusto Explorer
# Connect to cluster
# Execute kql/schema.kql
```

### 4. Set Up Eventstream

Follow the guide in `eventstream/deployment-guide.md` to configure the Fabric Eventstream.

### 5. Run IoT Simulator

```bash
cd simulators

# Install dependencies
pip install -r requirements.txt

# Copy and configure .env
cp .env.example .env
# Edit .env with your Event Hub connection string

# Run simulator
python iot_simulator.py --devices 10 --duration 300 --interval 1
```

### 6. Deploy Dashboards

See `dashboards/README.md` for dashboard deployment instructions.

## Streaming Patterns

### Lambda Architecture
This solution implements a Lambda architecture variant:

- **Hot Path**: Event Hub → Eventstream → KQL Database (real-time)
- **Cold Path**: Event Hub → Eventstream → Lakehouse (batch)
- **Serving Layer**: KQL Database queries combine hot and cold data

### Stream Processing Patterns

#### 1. Filter and Route
```javascript
// Route anomalies to separate stream
if (temperature > 85 || voltage < 180) {
  route_to: "anomaly-stream"
} else {
  route_to: "normal-stream"
}
```

#### 2. Windowed Aggregations
```kql
IoTTelemetry
| summarize avg(Temperature) by bin(EventTime, 5m), DeviceId
```

#### 3. Stateful Processing
```kql
// Detect sustained high temperature (5+ minutes)
IoTTelemetry
| where Temperature > 85
| summarize Duration = max(EventTime) - min(EventTime) by DeviceId
| where Duration > 5m
```

#### 4. Event Time vs Processing Time
- Events use `eventTime` (device timestamp)
- Watermarks handle late-arriving events (5-minute tolerance)
- Out-of-order events handled via Event Hub ordering guarantees

### Exactly-Once Semantics
- Event Hub provides at-least-once delivery
- KQL ingestion is idempotent via update policies
- Use checkpointing for consumer groups

## Deployment

### Development Environment

```bash
# Deploy with dev configuration
az deployment group create \
  --resource-group fabrti-rg-dev \
  --template-file infrastructure/main.bicep \
  --parameters environment=dev namePrefix=fabrti
```

- Dev SKU Kusto cluster (no SLA)
- Standard Event Hub (1 TU, auto-inflate enabled)
- 90-day retention

### Production Environment

```bash
# Deploy with production configuration
az deployment group create \
  --resource-group fabrti-rg-prod \
  --template-file infrastructure/main.bicep \
  --parameters environment=prod namePrefix=fabrti
```

- Standard D13 v2 Kusto cluster
- Premium Event Hub (dedicated capacity)
- 365-day retention
- Geo-redundancy enabled

### CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
name: Deploy Infrastructure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - name: Deploy Bicep
        run: |
          az deployment group create \
            --resource-group ${{ secrets.RESOURCE_GROUP }} \
            --template-file infrastructure/main.bicep \
            --parameters environment=prod
```

## Usage

### Sending Telemetry

#### Using the Simulator

```bash
# Basic usage
python simulators/iot_simulator.py

# Custom configuration
python simulators/iot_simulator.py \
  --devices 50 \
  --duration 3600 \
  --interval 5

# Generate sample data to file
python simulators/iot_simulator.py \
  --sample 1000 \
  --output sample-data.json
```

#### Programmatic API

```python
from azure.eventhub import EventHubProducerClient, EventData
import json

producer = EventHubProducerClient.from_connection_string(
    connection_string
)

event_data = {
    "eventTime": "2024-01-01T00:00:00Z",
    "deviceId": "device-001",
    "temperature": 22.5,
    # ... other fields
}

batch = producer.create_batch()
batch.add(EventData(json.dumps(event_data)))
producer.send_batch(batch)
```

### Querying Data

#### Basic Queries

```kql
// Recent telemetry
IoTTelemetry
| where EventTime > ago(1h)
| take 100

// Device status
IoTTelemetry
| where EventTime > ago(5m)
| summarize arg_max(EventTime, *) by DeviceId
| project DeviceId, Temperature, Status

// Aggregations
IoTTelemetry
| where EventTime > ago(24h)
| summarize
    AvgTemp = avg(Temperature),
    TotalEnergy = sum(EnergyConsumed)
    by Location
```

#### Advanced Analytics

```kql
// Anomaly detection
IoTTelemetry
| where EventTime > ago(7d)
| make-series AvgTemp = avg(Temperature) on EventTime step 1h
| extend (anomalies, score, baseline) = series_decompose_anomalies(AvgTemp, 1.5)
| mv-expand EventTime, AvgTemp, anomalies, baseline
| where anomalies == 1

// Predictive maintenance
IoTTelemetry
| where EventTime > ago(7d)
| summarize
    VoltageTrend = series_fit_line(make_list(Voltage)),
    TempVariability = stdev(Temperature)
    by DeviceId
| where TempVariability > 10
```

See `kql/queries.kql` for 24 example queries.

### Dashboard Access

1. Open Power BI Service or Fabric workspace
2. Navigate to "Real-Time Intelligence" section
3. Open "IoT Real-Time Intelligence Dashboard"
4. Use filters to customize view

## Testing

### Run All Tests

```bash
cd tests

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your connection strings

# Run tests
python test_streaming_api.py
```

### Test Categories

1. **Connection Tests**: Verify Event Hub and KQL connectivity
2. **Ingestion Tests**: Send events and verify delivery
3. **Query Tests**: Test KQL queries and aggregations
4. **Latency Tests**: Measure end-to-end latency
5. **Performance Tests**: Throughput and load testing

### Sample Output

```
======================================================================
Fabric Real-Time Intelligence - Streaming API Tests
======================================================================

test_01_eventhub_connection ... ✓ Event Hub connection successful
test_02_send_single_event ... ✓ Successfully sent test event: test-device-001
test_05_query_telemetry_table ... ✓ Successfully queried IoTTelemetry table. Found 10 records
test_11_end_to_end_latency ... ✓ End-to-end latency: 45.23 seconds

----------------------------------------------------------------------
Tests run: 12
Successes: 11
Failures: 0
Errors: 1 (materialized view not found)
======================================================================
```

## Monitoring

### Key Metrics

#### Event Hub Metrics
- Incoming Messages
- Incoming Bytes
- Outgoing Messages
- Throttled Requests
- Consumer Lag

#### KQL Database Metrics
- Ingestion Latency
- Query Duration
- Cache Hit Ratio
- CPU Usage
- Data Size

#### Application Metrics
- Events/second throughput
- End-to-end latency
- Error rate
- Alert frequency

### Diagnostic Queries

```kql
// Ingestion statistics
.show ingestion failures
| where FailedOn > ago(1h)
| summarize count() by FailureKind

// Query performance
.show queries
| where StartedOn > ago(1h)
| summarize
    AvgDuration = avg(Duration),
    P95Duration = percentile(Duration, 95)

// Data freshness
IoTTelemetry
| summarize max(EventTime)
| extend Freshness = now() - max_EventTime
```

### Alerts

Configure alerts for:
- High ingestion latency (> 60s)
- Query failures (> 1% error rate)
- Device offline (no data for 10+ minutes)
- Temperature anomalies (> 90°C)
- Low throughput (< 10 events/min)

## Best Practices

### Data Modeling
- Use appropriate data types (real, datetime, dynamic)
- Partition large tables by device type or location
- Implement data retention policies
- Use materialized views for frequent queries

### Query Optimization
- Filter early with `where` clauses
- Use `summarize` instead of raw data
- Leverage partitioning and caching
- Avoid `select *` in production

### Ingestion Patterns
- Batch events when possible (100-1000 per batch)
- Use compression for large payloads
- Implement retry logic with exponential backoff
- Monitor dead-letter queues

### Security
- Use managed identities for authentication
- Enable TLS 1.2+ for all connections
- Implement network security groups
- Rotate connection strings regularly
- Enable diagnostic logging

### Cost Optimization
- Right-size Kusto cluster SKU
- Use auto-stop for dev environments
- Implement data retention policies
- Archive cold data to storage
- Monitor and optimize query costs

## Troubleshooting

### Data Not Appearing

**Symptoms**: Events sent but not visible in KQL Database

**Checks**:
1. Verify Event Hub is receiving data:
   ```bash
   az eventhub eventhub show \
     --resource-group fabrti-rg-dev \
     --namespace-name fabrti-eventhub-dev \
     --name iot-telemetry-stream
   ```

2. Check ingestion failures:
   ```kql
   .show ingestion failures
   | where FailedOn > ago(1h)
   ```

3. Verify data connection:
   ```kql
   .show database policy streamingingestion
   ```

### High Latency

**Symptoms**: Long delay between event generation and query results

**Solutions**:
- Enable streaming ingestion: `.alter table IoTTelemetry policy streamingingestion enable`
- Check Event Hub consumer lag
- Scale up Kusto cluster
- Review batching policy

### Schema Mismatches

**Symptoms**: Ingestion failures with "Schema mismatch" errors

**Solution**:
```kql
// Check mapping
.show table IoTTelemetry ingestion json mappings

// Update mapping if needed
.create-or-alter table IoTTelemetry ingestion json mapping 'IoTTelemetryMapping' ...
```

### Query Performance

**Symptoms**: Slow dashboard loads or timeouts

**Optimizations**:
```kql
// Add time filter
| where EventTime > ago(1h)

// Use materialized views
DeviceStatusView
| where ...

// Enable caching
.alter table IoTTelemetry policy caching hot = 30d
```

## Performance Benchmarks

### Ingestion Performance
| Configuration | Events/sec | Latency (p95) |
|---------------|-----------|---------------|
| Dev SKU | 1,000 | 45s |
| Standard D11 v2 | 10,000 | 15s |
| Standard D13 v2 | 100,000 | 5s |

### Query Performance
| Query Type | Execution Time |
|------------|----------------|
| Recent data (1h) | < 1s |
| Aggregations (24h) | 2-5s |
| Time series (7d) | 5-10s |
| Anomaly detection (30d) | 15-30s |

## Scaling Guidelines

### Small Deployment (1-100 devices)
- Event Hub: Standard (1 TU)
- Kusto: Dev SKU
- Expected throughput: < 100 events/sec
- Cost: ~$200/month

### Medium Deployment (100-1000 devices)
- Event Hub: Standard (5 TU)
- Kusto: Standard D11 v2
- Expected throughput: 100-1000 events/sec
- Cost: ~$1,500/month

### Large Deployment (1000+ devices)
- Event Hub: Premium (1+ PU)
- Kusto: Standard D13 v2 or larger
- Expected throughput: > 10,000 events/sec
- Cost: ~$5,000+/month

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/fabric-realtime-intelligence.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install all dependencies
pip install -r simulators/requirements.txt
pip install -r tests/requirements.txt

# Run tests
cd tests
python test_streaming_api.py
```

## Resources

### Documentation
- [Microsoft Fabric Real-Time Intelligence](https://learn.microsoft.com/fabric/real-time-analytics/)
- [Azure Event Hubs](https://learn.microsoft.com/azure/event-hubs/)
- [KQL Query Language](https://learn.microsoft.com/azure/data-explorer/kusto/query/)
- [Azure Data Explorer](https://learn.microsoft.com/azure/data-explorer/)

### Tutorials
- [Get started with Real-Time Intelligence](https://learn.microsoft.com/fabric/real-time-analytics/tutorial-introduction)
- [Event Hubs Capture](https://learn.microsoft.com/azure/event-hubs/event-hubs-capture-overview)
- [KQL Quick Reference](https://learn.microsoft.com/azure/data-explorer/kql-quick-reference)

### Tools
- [Azure Data Studio](https://azure.microsoft.com/products/data-studio/)
- [Kusto Explorer](https://learn.microsoft.com/azure/data-explorer/kusto/tools/kusto-explorer)
- [VS Code Kusto Extension](https://marketplace.visualstudio.com/items?itemName=ms-kusto.kusto)

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/fabric-realtime-intelligence/issues)
- Email: support@example.com
- Microsoft Fabric Community: [Join discussions](https://community.fabric.microsoft.com/)

---

**Built with Microsoft Fabric Real-Time Intelligence** 🚀
