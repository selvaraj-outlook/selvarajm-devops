output "resource_group" {
  description = "Resource group name."
  value       = azurerm_resource_group.this.name
}

output "workspace_name" {
  description = "Azure ML workspace name (az ml ... -w)."
  value       = azurerm_machine_learning_workspace.this.name
}

output "compute_cluster" {
  description = "Training cluster name."
  value       = azurerm_machine_learning_compute_cluster.cpu.name
}

output "container_registry" {
  description = "Registry that AML builds environment images into."
  value       = azurerm_container_registry.this.login_server
}
