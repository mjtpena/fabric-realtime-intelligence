// Fabric Real-Time Intelligence Infrastructure
// This Bicep template deploys the core components for a real-time analytics solution

@description('The location for all resources')
param location string = resourceGroup().location

@description('The name prefix for all resources')
param namePrefix string = 'fabrti'

@description('Environment name (dev, test, prod)')
@allowed([
  'dev'
  'test'
  'prod'
])
param environment string = 'dev'

@description('Tags to apply to all resources')
param tags object = {
  Environment: environment
  Project: 'FabricRealTimeIntelligence'
  ManagedBy: 'Bicep'
}

// Variables
var fabricWorkspaceName = '${namePrefix}-workspace-${environment}'
var kqlDatabaseName = '${namePrefix}-kqldb-${environment}'
var eventHubNamespaceName = '${namePrefix}-eventhub-${environment}'
var eventHubName = 'iot-telemetry-stream'
var storageAccountName = '${namePrefix}storage${environment}'
var kqlClusterName = '${namePrefix}-kql-${environment}'

// Event Hub Namespace
resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: eventHubNamespaceName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    zoneRedundant: false
    isAutoInflateEnabled: true
    maximumThroughputUnits: 20
    kafkaEnabled: true
  }
}

// Event Hub for IoT Telemetry
resource eventHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  parent: eventHubNamespace
  name: eventHubName
  properties: {
    messageRetentionInDays: 7
    partitionCount: 4
    status: 'Active'
  }
}

// Event Hub Consumer Groups
resource consumerGroupKQL 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2024-01-01' = {
  parent: eventHub
  name: 'kql-ingestion'
  properties: {}
}

resource consumerGroupAnalytics 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2024-01-01' = {
  parent: eventHub
  name: 'analytics'
  properties: {}
}

// Authorization Rules
resource eventHubSendRule 'Microsoft.EventHub/namespaces/eventhubs/authorizationRules@2024-01-01' = {
  parent: eventHub
  name: 'SendRule'
  properties: {
    rights: [
      'Send'
    ]
  }
}

resource eventHubListenRule 'Microsoft.EventHub/namespaces/eventhubs/authorizationRules@2024-01-01' = {
  parent: eventHub
  name: 'ListenRule'
  properties: {
    rights: [
      'Listen'
    ]
  }
}

// Storage Account for cold path and checkpointing
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    encryption: {
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

// Blob Services
resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

// Container for raw telemetry data
resource rawDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'raw-telemetry'
  properties: {
    publicAccess: 'None'
  }
}

// Container for processed data
resource processedDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'processed-data'
  properties: {
    publicAccess: 'None'
  }
}

// Azure Data Explorer (Kusto) Cluster
resource kustoCluster 'Microsoft.Kusto/clusters@2023-08-15' = {
  name: kqlClusterName
  location: location
  tags: tags
  sku: {
    name: 'Dev(No SLA)_Standard_E2a_v4'
    tier: 'Basic'
    capacity: 1
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    enableStreamingIngest: true
    enablePurge: true
    enableDiskEncryption: false
    enableDoubleEncryption: false
    publicNetworkAccess: 'Enabled'
    allowedIpRangeList: []
    enableAutoStop: true
  }
}

// KQL Database
resource kustoDatabase 'Microsoft.Kusto/clusters/databases@2023-08-15' = {
  parent: kustoCluster
  name: kqlDatabaseName
  location: location
  kind: 'ReadWrite'
  properties: {
    softDeletePeriod: 'P365D'
    hotCachePeriod: 'P31D'
  }
}

// Data Connection from Event Hub to KQL Database
resource dataConnection 'Microsoft.Kusto/clusters/databases/dataConnections@2023-08-15' = {
  parent: kustoDatabase
  name: 'iot-telemetry-connection'
  location: location
  kind: 'EventHub'
  properties: {
    eventHubResourceId: eventHub.id
    consumerGroup: consumerGroupKQL.name
    tableName: 'IoTTelemetry'
    mappingRuleName: 'IoTTelemetryMapping'
    dataFormat: 'JSON'
    compression: 'None'
    managedIdentityResourceId: kustoCluster.id
    databaseRouting: 'Single'
  }
  dependsOn: [
    kustoCluster
  ]
}

// Role assignment for Event Hub access
resource eventHubRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: eventHub
  name: guid(eventHub.id, kustoCluster.id, 'Azure Event Hubs Data Receiver')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a638d3c7-ab3a-418d-83e6-5f17a39d4fde')
    principalId: kustoCluster.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output eventHubNamespaceName string = eventHubNamespace.name
output eventHubName string = eventHub.name
output eventHubConnectionString string = eventHubSendRule.listKeys().primaryConnectionString
output kustoClusterUri string = kustoCluster.properties.uri
output kustoDatabaseName string = kustoDatabase.name
output storageAccountName string = storageAccount.name
output storageAccountKey string = storageAccount.listKeys().keys[0].value
output resourceGroupName string = resourceGroup().name
