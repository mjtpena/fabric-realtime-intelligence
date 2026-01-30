# Fabric Real-Time Intelligence Infrastructure - Terraform
# This Terraform configuration deploys the core components for a real-time analytics solution

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# Variables
variable "location" {
  description = "The Azure region for all resources"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be dev, test, or prod."
  }
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "fabrti"
}

# Local variables
locals {
  resource_group_name      = "${var.name_prefix}-rg-${var.environment}"
  eventhub_namespace_name  = "${var.name_prefix}-eventhub-${var.environment}"
  eventhub_name           = "iot-telemetry-stream"
  storage_account_name    = "${var.name_prefix}storage${var.environment}"
  kusto_cluster_name      = "${var.name_prefix}-kql-${var.environment}"
  kusto_database_name     = "${var.name_prefix}-kqldb-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = "FabricRealTimeIntelligence"
    ManagedBy   = "Terraform"
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = local.resource_group_name
  location = var.location
  tags     = local.tags
}

# Event Hub Namespace
resource "azurerm_eventhub_namespace" "main" {
  name                     = local.eventhub_namespace_name
  location                 = azurerm_resource_group.main.location
  resource_group_name      = azurerm_resource_group.main.name
  sku                      = "Standard"
  capacity                 = 1
  auto_inflate_enabled     = true
  maximum_throughput_units = 20
  minimum_tls_version      = "1.2"

  tags = local.tags
}

# Event Hub
resource "azurerm_eventhub" "iot_telemetry" {
  name                = local.eventhub_name
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = 4
  message_retention   = 7
}

# Event Hub Consumer Groups
resource "azurerm_eventhub_consumer_group" "kql_ingestion" {
  name                = "kql-ingestion"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.iot_telemetry.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "analytics" {
  name                = "analytics"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.iot_telemetry.name
  resource_group_name = azurerm_resource_group.main.name
}

# Event Hub Authorization Rules
resource "azurerm_eventhub_authorization_rule" "send" {
  name                = "SendRule"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.iot_telemetry.name
  resource_group_name = azurerm_resource_group.main.name

  listen = false
  send   = true
  manage = false
}

resource "azurerm_eventhub_authorization_rule" "listen" {
  name                = "ListenRule"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.iot_telemetry.name
  resource_group_name = azurerm_resource_group.main.name

  listen = true
  send   = false
  manage = false
}

# Storage Account
resource "azurerm_storage_account" "main" {
  name                     = local.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  access_tier              = "Hot"

  min_tls_version           = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }

  tags = local.tags
}

# Storage Containers
resource "azurerm_storage_container" "raw_telemetry" {
  name                  = "raw-telemetry"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "processed_data" {
  name                  = "processed-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Azure Data Explorer (Kusto) Cluster
resource "azurerm_kusto_cluster" "main" {
  name                = local.kusto_cluster_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  sku {
    name     = "Dev(No SLA)_Standard_E2a_v4"
    capacity = 1
  }

  identity {
    type = "SystemAssigned"
  }

  streaming_ingestion_enabled = true
  purge_enabled              = true
  auto_stop_enabled          = true

  tags = local.tags
}

# KQL Database
resource "azurerm_kusto_database" "main" {
  name                = local.kusto_database_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  cluster_name        = azurerm_kusto_cluster.main.name

  soft_delete_period = "P365D"
  hot_cache_period   = "P31D"
}

# Event Hub Data Connection
resource "azurerm_kusto_eventhub_data_connection" "main" {
  name                = "iot-telemetry-connection"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  cluster_name        = azurerm_kusto_cluster.main.name
  database_name       = azurerm_kusto_database.main.name

  eventhub_id    = azurerm_eventhub.iot_telemetry.id
  consumer_group = azurerm_eventhub_consumer_group.kql_ingestion.name

  table_name        = "IoTTelemetry"
  mapping_rule_name = "IoTTelemetryMapping"
  data_format       = "JSON"
  compression       = "None"

  identity_id = azurerm_kusto_cluster.main.id
}

# Role Assignment for Event Hub access
resource "azurerm_role_assignment" "eventhub_receiver" {
  scope                = azurerm_eventhub.iot_telemetry.id
  role_definition_name = "Azure Event Hubs Data Receiver"
  principal_id         = azurerm_kusto_cluster.main.identity[0].principal_id
}

# Outputs
output "eventhub_namespace_name" {
  value       = azurerm_eventhub_namespace.main.name
  description = "The name of the Event Hub namespace"
}

output "eventhub_name" {
  value       = azurerm_eventhub.iot_telemetry.name
  description = "The name of the Event Hub"
}

output "eventhub_connection_string" {
  value       = azurerm_eventhub_authorization_rule.send.primary_connection_string
  description = "Event Hub connection string for sending data"
  sensitive   = true
}

output "kusto_cluster_uri" {
  value       = azurerm_kusto_cluster.main.uri
  description = "The URI of the Kusto cluster"
}

output "kusto_database_name" {
  value       = azurerm_kusto_database.main.name
  description = "The name of the KQL database"
}

output "storage_account_name" {
  value       = azurerm_storage_account.main.name
  description = "The name of the storage account"
}

output "resource_group_name" {
  value       = azurerm_resource_group.main.name
  description = "The name of the resource group"
}
