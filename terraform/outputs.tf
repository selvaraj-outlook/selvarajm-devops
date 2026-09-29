output "node_role_name" {
  description = "Set as spec.role in the EC2NodeClass."
  value       = aws_iam_role.node.name
}

output "controller_role_arn" {
  description = "Karpenter controller IRSA role."
  value       = aws_iam_role.controller.arn
}

output "interruption_queue" {
  description = "SQS queue receiving interruption events."
  value       = aws_sqs_queue.interruption.name
}
