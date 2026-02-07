output "zone_id" {
  description = "Route 53 hosted zone ID"
  value       = aws_route53_zone.main.zone_id
}

output "name_servers" {
  description = "Name servers for the hosted zone"
  value       = aws_route53_zone.main.name_servers
}

output "domain_name" {
  description = "Domain name of the hosted zone"
  value       = aws_route53_zone.main.name
}

output "apex_record_fqdn" {
  description = "FQDN of the apex A record"
  value       = aws_route53_record.apex.fqdn
}

output "api_subdomain_fqdn" {
  description = "FQDN of the api subdomain (if created)"
  value       = var.create_api_subdomain ? aws_route53_record.api[0].fqdn : null
}

output "www_subdomain_fqdn" {
  description = "FQDN of the www subdomain (if created)"
  value       = var.create_www_subdomain ? aws_route53_record.www[0].fqdn : null
}
