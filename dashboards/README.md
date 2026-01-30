# Real-Time Intelligence Dashboards

## Overview
This directory contains dashboard definitions for monitoring and analyzing IoT telemetry data in real-time using Microsoft Fabric Real-Time Intelligence.

## Dashboard: IoT Real-Time Intelligence

### Features
- **Real-time monitoring**: Auto-refresh every 30 seconds
- **Interactive filters**: Location and device type selection
- **Multiple visualizations**: Charts, maps, tables, and statistics
- **Anomaly detection**: Built-in ML-based anomaly detection
- **Alerting**: Configurable alerts for critical conditions

### Tiles

#### Key Metrics (Row 1)
1. **Active Devices**: Total count of devices reporting in the selected time range
2. **Total Events**: Number of telemetry events received
3. **Active Alerts**: Current alert count with color-coded thresholds
4. **Average Temperature**: Overall average temperature across all devices

#### Time Series Charts (Rows 2-3)
5. **Temperature Trend by Location**: Line chart showing temperature patterns
6. **Humidity Trend by Location**: Line chart showing humidity patterns
7. **Power Consumption Over Time**: Area chart of total power usage

#### Distribution Charts (Row 4)
8. **Device Status Distribution**: Pie chart showing healthy vs unhealthy devices
9. **Devices by Location**: Bar chart of device count per location
10. **Top 10 Energy Consumers**: Horizontal bar chart of highest energy users

#### Data Tables (Row 5)
11. **Recent Alerts**: Sortable table of latest alerts with severity indicators
12. **Device Health Summary by Location**: Comprehensive health metrics per location

#### Advanced Analytics (Row 6)
13. **Device Geographic Distribution**: Interactive map showing device locations and status
14. **Temperature Anomaly Detection**: ML-based anomaly detection with baseline

## Deployment

### Power BI Real-Time Dashboard

1. **Create Power BI Streaming Dataset**:
```bash
# Using Power BI REST API
POST https://api.powerbi.com/v1.0/myorg/datasets
{
  "name": "IoT-RealTime-Metrics",
  "tables": [{
    "name": "LiveMetrics",
    "columns": [...]
  }]
}
```

2. **Import Dashboard JSON**:
   - Open Power BI Service
   - Navigate to your workspace
   - Click "New" → "Dashboard"
   - Use "Import dashboard from JSON" feature

3. **Configure Data Source**:
   - Set KQL Database connection
   - Enter cluster URI and database name
   - Configure authentication (Azure AD)

### Fabric Real-Time Dashboard

1. **Create Dashboard in Fabric**:
```bash
# Using Fabric REST API
POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/dashboards
Content-Type: application/json

{
  "displayName": "IoT Real-Time Intelligence",
  "definition": {
    "parts": [...]
  }
}
```

2. **Connect to KQL Database**:
   - Data source type: Kusto
   - Cluster URI: Your KQL cluster endpoint
   - Database: Your database name

3. **Configure Refresh**:
   - Enable auto-refresh
   - Set interval: 30 seconds
   - Configure cache settings

### Azure Managed Grafana (Alternative)

1. **Install Grafana Dashboard**:
```bash
# Import dashboard JSON
curl -X POST \
  http://grafana-instance/api/dashboards/import \
  -H 'Content-Type: application/json' \
  -d @realtime-dashboard.json
```

2. **Configure Azure Data Explorer Plugin**:
   - Install ADX datasource plugin
   - Configure cluster connection
   - Set up authentication

## Customization

### Adding New Tiles

Example: Add a voltage monitoring tile
```json
{
  "id": "voltage-trend",
  "type": "chart",
  "title": "Voltage Trend",
  "position": {"x": 0, "y": 19, "w": 6, "h": 3},
  "query": "IoTTelemetry | where EventTime > ago({timeRange}) | summarize AvgVoltage = avg(Voltage) by bin(EventTime, 5m) | render timechart",
  "visualization": {
    "type": "lineChart",
    "xAxis": "EventTime",
    "yAxis": "AvgVoltage",
    "yAxisLabel": "Voltage (V)"
  }
}
```

### Modifying Queries

All queries use KQL (Kusto Query Language). Key patterns:

**Time filtering**:
```kql
| where EventTime > ago({timeRange})
```

**Aggregations**:
```kql
| summarize avg(Temperature) by bin(EventTime, 5m), Location
```

**Filtering by variables**:
```kql
| where Location in ({selectedLocation}) or '{selectedLocation}' == 'All'
```

### Color Schemes

Customize appearance in the dashboard JSON:
```json
"appearance": {
  "theme": "dark",           // or "light"
  "primaryColor": "#0078D4", // Azure blue
  "backgroundColor": "#1E1E1E"
}
```

## Alerting

### Configure Alert Rules

Alerts are defined in the `alerts` section of the JSON:

```json
{
  "name": "Custom Alert",
  "condition": "KQL query that returns count",
  "severity": "High",
  "notification": {
    "email": ["alerts@example.com"],
    "webhook": "https://webhook-url.com"
  }
}
```

### Available Severities
- **Critical**: Immediate action required
- **High**: Important but not critical
- **Medium**: Should be addressed soon
- **Low**: Informational

### Testing Alerts

Manually trigger an alert:
```kql
// Simulate high temperature condition
.ingest inline into table IoTTelemetry <|
{
  "eventTime": "2024-01-01T00:00:00Z",
  "deviceId": "test-device-001",
  "temperature": 95.0,
  ...
}
```

## Performance Optimization

### Query Optimization
- Use materialized views for frequently accessed aggregations
- Leverage partitioning for large datasets
- Cache static reference data

### Dashboard Performance
- Limit time ranges for expensive queries
- Use sampling for large result sets
- Implement progressive loading for tables

### Example: Optimized Query
```kql
// Instead of scanning full table
IoTTelemetry
| where EventTime > ago(1h)
| summarize avg(Temperature) by DeviceId

// Use materialized view
DeviceStatusView
| where EventTime > ago(1h)
| summarize avg(Temperature) by DeviceId
```

## Monitoring Dashboard Health

### Key Metrics to Monitor
- Query execution time
- Refresh success rate
- Data freshness
- Alert trigger frequency

### Diagnostic Query
```kql
.show queries
| where StartedOn > ago(1h)
| where Text contains "Dashboard"
| summarize
    AvgDuration = avg(Duration),
    MaxDuration = max(Duration),
    FailureRate = countif(State == "Failed") * 100.0 / count()
  by QueryHash = hash_sha256(Text)
```

## Best Practices

1. **Time Range Management**
   - Default to 1 hour for real-time views
   - Provide variable controls for user customization
   - Cache historical data for longer time ranges

2. **Visual Hierarchy**
   - Place key metrics at the top
   - Group related visualizations together
   - Use consistent color schemes

3. **Query Efficiency**
   - Use `summarize` instead of raw data
   - Implement proper filtering
   - Leverage table indexes

4. **User Experience**
   - Enable drill-through capabilities
   - Provide tooltips for complex metrics
   - Include refresh timestamps

5. **Accessibility**
   - Use high-contrast colors
   - Provide alternative text for visuals
   - Support keyboard navigation

## Troubleshooting

### Common Issues

#### Dashboard Not Refreshing
- Check auto-refresh settings
- Verify KQL database connection
- Review query execution logs

#### Slow Query Performance
```kql
// Diagnose slow queries
.show queries
| where Duration > 10s
| project StartedOn, Duration, Text
| order by Duration desc
```

#### Missing Data
- Verify Eventstream is running
- Check ingestion lag
- Review time zone settings

## Examples

### Custom Location Dashboard

Create a location-specific view:
```json
{
  "name": "Seattle Operations Dashboard",
  "filters": {
    "location": "Seattle"
  },
  "tiles": [
    // Location-specific tiles
  ]
}
```

### Executive Summary Dashboard

High-level metrics for management:
```json
{
  "name": "Executive Summary",
  "refreshInterval": 300,
  "tiles": [
    // KPI tiles only
    // Trend charts
    // SLA metrics
  ]
}
```

## Resources

- [Power BI Real-Time Streaming](https://learn.microsoft.com/power-bi/connect-data/service-real-time-streaming)
- [Fabric Real-Time Dashboards](https://learn.microsoft.com/fabric/real-time-analytics/dashboard-real-time-create)
- [KQL Query Best Practices](https://learn.microsoft.com/azure/data-explorer/kusto/query/best-practices)
- [Azure Managed Grafana](https://learn.microsoft.com/azure/managed-grafana/)
