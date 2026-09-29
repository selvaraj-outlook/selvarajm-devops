data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  base   = "${var.name}-${var.environment}"
  unique = "${var.name}${var.environment}${random_string.suffix.result}"
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.base}"
  location = var.location
  tags     = var.tags
}

################################################################################
# Workspace dependencies
################################################################################

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${local.base}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = "appi-${local.base}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
  tags                = var.tags
}

resource "azurerm_key_vault" "this" {
  name                       = substr("kv${local.unique}", 0, 24)
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  enable_rbac_authorization  = true
  tags                       = var.tags
}

resource "azurerm_storage_account" "this" {
  name                            = substr("st${local.unique}", 0, 24)
  location                        = azurerm_resource_group.this.location
  resource_group_name             = azurerm_resource_group.this.name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = true # the AML workspace still needs key access for its default datastore
  tags                            = var.tags

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
  }
}

resource "azurerm_container_registry" "this" {
  name                = substr("cr${local.unique}", 0, 50)
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "Basic"
  admin_enabled       = false
  tags                = var.tags
}

################################################################################
# Azure Machine Learning workspace + training cluster
################################################################################

resource "azurerm_machine_learning_workspace" "this" {
  name                          = "mlw-${local.base}"
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  application_insights_id       = azurerm_application_insights.this.id
  key_vault_id                  = azurerm_key_vault.this.id
  storage_account_id            = azurerm_storage_account.this.id
  container_registry_id         = azurerm_container_registry.this.id
  public_network_access_enabled = var.public_network_access
  v1_legacy_mode_enabled        = false
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_machine_learning_compute_cluster" "cpu" {
  name                          = "cpu-cluster"
  location                      = azurerm_resource_group.this.location
  machine_learning_workspace_id = azurerm_machine_learning_workspace.this.id
  vm_size                       = var.cpu_cluster_vm_size
  vm_priority                   = var.cpu_cluster_priority
  local_auth_enabled            = false

  scale_settings {
    min_node_count                       = 0
    max_node_count                       = var.cpu_cluster_max_nodes
    scale_down_nodes_after_idle_duration = "PT10M"
  }

  identity {
    type = "SystemAssigned"
  }
}

# Let the training cluster read and write the default datastore with its identity.
resource "azurerm_role_assignment" "cluster_blob" {
  scope                = azurerm_storage_account.this.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_machine_learning_compute_cluster.cpu.identity[0].principal_id
}
