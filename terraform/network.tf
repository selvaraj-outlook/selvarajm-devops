################################################################################
# Network: existing VPC. The private subnets have no outbound route, so nodes
# cannot reach the EKS API, ECR or STS. A NAT gateway in a public subnet fixes that.
################################################################################

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "${var.cluster_name}-nat" }
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = var.nat_public_subnet_id
  tags          = { Name = "${var.cluster_name}-nat" }
}

data "aws_route_table" "private" {
  for_each  = toset(var.subnet_ids)
  subnet_id = each.value
}

resource "aws_route" "private_nat" {
  for_each               = toset([for rt in data.aws_route_table.private : rt.id])
  route_table_id         = each.value
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this.id
}
