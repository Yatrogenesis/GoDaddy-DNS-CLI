"""
FastAPI Web Server for GoDaddy DNS CLI
Modern web interface with real-time updates
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from godaddy_cli.core.config import ConfigManager
from godaddy_cli.core.auth import AuthManager
from godaddy_cli.core.api_client import GoDaddyAPIClient, DNSRecord, Domain

app = FastAPI(
    title="GoDaddy DNS CLI Web Interface",
    description="Modern web interface for GoDaddy DNS management",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
config_manager: Optional[ConfigManager] = None
auth_manager: Optional[AuthManager] = None
websocket_connections: List[WebSocket] = []

# Pydantic models
class DNSRecordRequest(BaseModel):
    name: str
    type: str
    data: str
    ttl: int = 3600
    priority: Optional[int] = None

class DNSRecordUpdate(BaseModel):
    name: str
    type: str
    data: str
    ttl: int = 3600
    priority: Optional[int] = None

class BulkOperation(BaseModel):
    operation: str  # create, update, delete
    records: List[DNSRecordRequest]

class TemplateRequest(BaseModel):
    template_name: str
    variables: Dict[str, Any]

# Dependencies
def get_config() -> ConfigManager:
    global config_manager
    if not config_manager:
        raise HTTPException(status_code=500, detail="Configuration not initialized")
    return config_manager

def get_auth() -> AuthManager:
    global auth_manager
    if not auth_manager:
        raise HTTPException(status_code=500, detail="Authentication not initialized")
    return auth_manager

async def get_api_client(auth: AuthManager = Depends(get_auth)) -> GoDaddyAPIClient:
    """Get authenticated API client"""
    if not auth.is_configured():
        raise HTTPException(status_code=401, detail="API credentials not configured")
    return GoDaddyAPIClient(auth)

# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        websocket_connections.remove(websocket)

async def broadcast_update(message: Dict[str, Any]):
    """Broadcast update to all connected clients"""
    for connection in websocket_connections[:]:
        try:
            await connection.send_json(message)
        except:
            websocket_connections.remove(connection)

# API Routes

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

@app.get("/api/config/status")
async def get_config_status(config: ConfigManager = Depends(get_config),
                           auth: AuthManager = Depends(get_auth)):
    """Get configuration and authentication status"""
    return {
        "config_file": str(config.config_file),
        "profile": config.profile,
        "api_configured": auth.is_configured(),
        "profiles": list(config.list_profiles().keys())
    }

@app.get("/api/domains", response_model=List[Dict[str, Any]])
async def list_domains(auth: AuthManager = Depends(get_auth)):
    """List all domains"""
    try:
        async with GoDaddyAPIClient(auth) as client:
            domains = await client.list_domains()
            return [
                {
                    "domain": domain.domain,
                    "status": domain.status,
                    "expires": domain.expires,
                    "created": domain.created,
                    "privacy": domain.privacy,
                    "locked": domain.locked
                }
                for domain in domains
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/domains/{domain}/records", response_model=List[Dict[str, Any]])
async def get_dns_records(domain: str, record_type: Optional[str] = None,
                         auth: AuthManager = Depends(get_auth)):
    """Get DNS records for a domain"""
    try:
        async with GoDaddyAPIClient(auth) as client:
            records = await client.list_dns_records(domain, record_type)
            return [
                {
                    "name": record.name,
                    "type": record.type,
                    "data": record.data,
                    "ttl": record.ttl,
                    "priority": record.priority
                }
                for record in records
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/domains/{domain}/records")
async def create_dns_record(domain: str, record: DNSRecordRequest,
                           background_tasks: BackgroundTasks,
                           auth: AuthManager = Depends(get_auth)):
    """Create a new DNS record"""
    try:
        dns_record = DNSRecord(
            name=record.name,
            type=record.type,
            data=record.data,
            ttl=record.ttl,
            priority=record.priority
        )

        async with GoDaddyAPIClient(auth) as client:
            success = await client.create_dns_record(domain, dns_record)

        if success:
            # Broadcast update to connected clients
            background_tasks.add_task(
                broadcast_update,
                {
                    "type": "record_created",
                    "domain": domain,
                    "record": record.dict()
                }
            )
            return {"success": True, "message": "DNS record created"}
        else:
            raise HTTPException(status_code=400, detail="Failed to create DNS record")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/domains/{domain}/records/{record_type}/{record_name}")
async def update_dns_record(domain: str, record_type: str, record_name: str,
                           record: DNSRecordUpdate,
                           background_tasks: BackgroundTasks,
                           auth: AuthManager = Depends(get_auth)):
    """Update an existing DNS record"""
    try:
        dns_record = DNSRecord(
            name=record.name,
            type=record.type,
            data=record.data,
            ttl=record.ttl,
            priority=record.priority
        )

        async with GoDaddyAPIClient(auth) as client:
            success = await client.update_dns_record(domain, dns_record)

        if success:
            background_tasks.add_task(
                broadcast_update,
                {
                    "type": "record_updated",
                    "domain": domain,
                    "record": record.dict()
                }
            )
            return {"success": True, "message": "DNS record updated"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update DNS record")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/domains/{domain}/records/{record_type}/{record_name}")
async def delete_dns_record(domain: str, record_type: str, record_name: str,
                           background_tasks: BackgroundTasks,
                           auth: AuthManager = Depends(get_auth)):
    """Delete a DNS record"""
    try:
        async with GoDaddyAPIClient(auth) as client:
            success = await client.delete_dns_record(domain, record_type, record_name)

        if success:
            background_tasks.add_task(
                broadcast_update,
                {
                    "type": "record_deleted",
                    "domain": domain,
                    "record_type": record_type,
                    "record_name": record_name
                }
            )
            return {"success": True, "message": "DNS record deleted"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete DNS record")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/domains/{domain}/bulk")
async def bulk_operations(domain: str, operation: BulkOperation,
                         background_tasks: BackgroundTasks,
                         auth: AuthManager = Depends(get_auth)):
    """Perform bulk operations on DNS records"""
    try:
        records = [
            DNSRecord(
                name=r.name,
                type=r.type,
                data=r.data,
                ttl=r.ttl,
                priority=r.priority
            )
            for r in operation.records
        ]

        async with GoDaddyAPIClient(auth) as client:
            if operation.operation == "create":
                result = await client.bulk_update_records(domain, records)
            elif operation.operation == "replace":
                result = await client.replace_all_records(domain, records)
            else:
                raise HTTPException(status_code=400, detail="Unsupported bulk operation")

        background_tasks.add_task(
            broadcast_update,
            {
                "type": "bulk_operation",
                "domain": domain,
                "operation": operation.operation,
                "result": result
            }
        )

        return {"success": True, "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/templates")
async def list_templates(config: ConfigManager = Depends(get_config)):
    """List available DNS templates"""
    templates_dir = config.config_dir / 'templates'
    templates = []

    if templates_dir.exists():
        for template_file in templates_dir.glob('*.yaml'):
            try:
                import yaml
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)
                    templates.append({
                        'name': template_data.get('name', template_file.stem),
                        'description': template_data.get('description', ''),
                        'version': template_data.get('version', '1.0.0'),
                        'file': template_file.name
                    })
            except Exception:
                continue

    return templates

@app.post("/api/domains/{domain}/template")
async def apply_template(domain: str, template_req: TemplateRequest,
                        background_tasks: BackgroundTasks,
                        config: ConfigManager = Depends(get_config),
                        auth: AuthManager = Depends(get_auth)):
    """Apply a DNS template to a domain"""
    try:
        from godaddy_cli.commands.template import _find_template, _generate_records
        import yaml

        template_path = _find_template(config, template_req.template_name)
        if not template_path:
            raise HTTPException(status_code=404, detail="Template not found")

        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)

        # Add domain to variables
        variables = template_req.variables.copy()
        variables['domain'] = domain

        # Generate records
        records = _generate_records(template_data, variables)

        if not records:
            raise HTTPException(status_code=400, detail="No records generated from template")

        # Apply to domain
        async with GoDaddyAPIClient(auth) as client:
            result = await client.bulk_update_records(domain, records)

        background_tasks.add_task(
            broadcast_update,
            {
                "type": "template_applied",
                "domain": domain,
                "template": template_req.template_name,
                "result": result
            }
        )

        return {"success": True, "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/domains/{domain}/validate")
async def validate_domain_dns(domain: str, auth: AuthManager = Depends(get_auth)):
    """Validate DNS configuration for a domain"""
    try:
        async with GoDaddyAPIClient(auth) as client:
            records = await client.list_dns_records(domain)

        # Validation logic (similar to CLI validate command)
        issues = []
        warnings = []
        suggestions = []

        a_records = [r for r in records if r.type == 'A']
        aaaa_records = [r for r in records if r.type == 'AAAA']
        mx_records = [r for r in records if r.type == 'MX']
        cname_records = [r for r in records if r.type == 'CNAME']

        # No A record for root domain
        if not any(r.name == '@' for r in a_records):
            issues.append("No A record for root domain (@)")

        # CNAME conflicts
        for cname in cname_records:
            conflicting = [r for r in records
                         if r.name == cname.name and r.type != 'CNAME']
            if conflicting:
                issues.append(f"CNAME record '{cname.name}' conflicts with {len(conflicting)} other record(s)")

        # TTL recommendations
        low_ttl_records = [r for r in records if r.ttl < 300]
        if low_ttl_records:
            warnings.append(f"{len(low_ttl_records)} record(s) have very low TTL (<300s)")

        high_ttl_records = [r for r in records if r.ttl > 86400]
        if high_ttl_records:
            suggestions.append(f"{len(high_ttl_records)} record(s) have very high TTL (>24h)")

        # Missing common records
        if not any(r.name == 'www' for r in records):
            suggestions.append("Consider adding a 'www' record")

        return {
            "domain": domain,
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions,
            "record_count": len(records)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files and React app
@app.get("/", response_class=HTMLResponse)
async def serve_app():
    """Serve the React application"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GoDaddy DNS CLI</title>
        <link rel="icon" href="/static/favicon.ico">
    </head>
    <body>
        <div id="root"></div>
        <script src="/static/js/bundle.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

def start_server(host: str = "127.0.0.1", port: int = 8080,
                config: Optional[ConfigManager] = None):
    """Start the web server"""
    global config_manager, auth_manager

    # Initialize global state
    config_manager = config or ConfigManager()
    auth_manager = AuthManager(config_manager)

    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False
    )

def main():
    """Main entry point for web server"""
    import click

    @click.command()
    @click.option('--host', default='127.0.0.1', help='Host to bind to')
    @click.option('--port', default=8080, help='Port to bind to')
    @click.option('--profile', default='default', help='Configuration profile')
    def run_server(host, port, profile):
        """Run the GoDaddy DNS CLI web server"""
        config = ConfigManager(profile=profile)
        start_server(host, port, config)

    run_server()

if __name__ == "__main__":
    main()