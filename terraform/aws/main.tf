variable "my_ip" {
  type = string
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

resource "aws_vpc" "lab" {
  cidr_block = "10.42.0.0/16"
  tags       = { Name = "sre-lab-vpc" }
}

resource "aws_subnet" "lab" {
  vpc_id                  = aws_vpc.lab.id
  cidr_block              = "10.42.1.0/24"
  tags                    = { Name = "sre-lab-subnet" }
  map_public_ip_on_launch = true
}

resource "aws_security_group" "ssh" {
  vpc_id = aws_vpc.lab.id
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  ingress {
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_key_pair" "lab" {
  key_name   = "sre-lab-key"
  public_key = file("~/.ssh/sre-lab.pub")
}

# Internet gateway — the VPC's edge router to the outside world
resource "aws_internet_gateway" "lab" {
  vpc_id = aws_vpc.lab.id
  tags   = { Name = "sre-lab-igw" }
}

# Route table: send non-local traffic to the IGW
resource "aws_route_table" "lab" {
  vpc_id = aws_vpc.lab.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lab.id
  }

  tags = { Name = "sre-lab-rt" }
}

# Attach the route table to our subnet
resource "aws_route_table_association" "lab" {
  subnet_id      = aws_subnet.lab.id
  route_table_id = aws_route_table.lab.id
}

# Look up the latest Ubuntu 24.04 AMI instead of hardcoding an ID
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical's official AWS account

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "node" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "m7i-flex.large"
  subnet_id              = aws_subnet.lab.id
  vpc_security_group_ids = [aws_security_group.ssh.id]
  key_name               = aws_key_pair.lab.key_name
  user_data              = file("user_data.sh")

  tags = { Name = "sre-lab-node-1" }
}

output "node_public_ip" {
  value = aws_instance.node.public_ip
}