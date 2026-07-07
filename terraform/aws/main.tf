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
  vpc_id     = aws_vpc.lab.id
  cidr_block = "10.42.1.0/24"
  tags       = { Name = "sre-lab-subnet" }
}

resource "aws_security_group" "ssh" {
  vpc_id = aws_vpc.lab.id
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # lab only
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}