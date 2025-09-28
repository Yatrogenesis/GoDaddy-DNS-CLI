#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoDaddy DNS Auto-Setup CLI
Similar a Wrangler pero para GoDaddy DNS
Enterprise-grade DNS management tool
"""

import requests
import json
import sys
import os
import time
from typing import Dict, Any, Optional, List
import argparse
from datetime import datetime, timedelta
import subprocess

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

class GoDaddyDNSManager:
    """
    CLI para manejar DNS de GoDaddy automáticamente
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or os.getenv('GODADDY_API_KEY')
        self.api_secret = api_secret or os.getenv('GODADDY_API_SECRET')
        self.base_url = "https://api.godaddy.com/v1"
        self.headers = {
            'Authorization': f'sso-key {self.api_key}:{self.api_secret}',
            'Content-Type': 'application/json'
        }

    def setup_cname(self, domain: str, subdomain: str, target: str) -> Dict[str, Any]:
        """
        Configurar CNAME automáticamente
        """
        print(f"🔧 Configurando CNAME: {subdomain}.{domain} -> {target}")

        # Preparar datos del registro CNAME
        dns_record = [{
            "type": "CNAME",
            "name": subdomain,
            "data": target,
            "ttl": 600  # 10 minutos
        }]

        try:
            # API call para crear/actualizar CNAME
            url = f"{self.base_url}/domains/{domain}/records/CNAME/{subdomain}"
            response = requests.put(url, headers=self.headers, json=dns_record)

            if response.status_code == 200:
                print(f"✅ CNAME configurado exitosamente")
                print(f"   {subdomain}.{domain} -> {target}")
                print(f"   TTL: 10 minutos")
                return {
                    "success": True,
                    "subdomain": f"{subdomain}.{domain}",
                    "target": target,
                    "ttl": 600
                }
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   {response.text}")
                return {"success": False, "error": response.text}

        except Exception as e:
            print(f"❌ Error de conexión: {str(e)}")
            return {"success": False, "error": str(e)}

    def list_dns_records(self, domain: str) -> Dict[str, Any]:
        """
        Listar todos los registros DNS
        """
        try:
            url = f"{self.base_url}/domains/{domain}/records"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                records = response.json()
                print(f"📋 Registros DNS para {domain}:")
                for record in records:
                    print(f"   {record['type']} | {record['name']} -> {record['data']}")
                return {"success": True, "records": records}
            else:
                print(f"❌ Error listando registros: {response.status_code}")
                return {"success": False, "error": response.text}

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {"success": False, "error": str(e)}

    def delete_record(self, domain: str, record_type: str, name: str) -> Dict[str, Any]:
        """
        Eliminar un registro DNS
        """
        try:
            url = f"{self.base_url}/domains/{domain}/records/{record_type}/{name}"
            response = requests.delete(url, headers=self.headers)

            if response.status_code == 204:
                print(f"🗑️ Registro eliminado: {record_type} {name}")
                return {"success": True}
            else:
                print(f"❌ Error eliminando: {response.status_code}")
                return {"success": False, "error": response.text}

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {"success": False, "error": str(e)}

    def check_domain_info(self, domain: str) -> Dict[str, Any]:
        """
        Verificar información del dominio
        """
        try:
            url = f"{self.base_url}/domains/{domain}"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                domain_info = response.json()
                print(f"ℹ️ Información de {domain}:")
                print(f"   Estado: {domain_info.get('status', 'N/A')}")
                print(f"   Nameservers: {domain_info.get('nameServers', [])}")
                return {"success": True, "info": domain_info}
            else:
                print(f"❌ Error: {response.status_code}")
                return {"success": False, "error": response.text}

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {"success": False, "error": str(e)}

    def setup_creator_subdomain(self) -> Dict[str, Any]:
        """
        Configuración específica para creator.avermex.com con monitoring
        """
        print("🚀 Configurando creator.avermex.com automáticamente...")

        # Verificar dominio primero
        domain_check = self.check_domain_info("avermex.com")
        if not domain_check["success"]:
            return domain_check

        # Configurar CNAME
        result = self.setup_cname(
            domain="avermex.com",
            subdomain="creator",
            target="aion-creator.pages.dev"
        )

        if result["success"]:
            print("\n🎉 ¡Configuración completada!")
            print("📍 URL final: https://creator.avermex.com")
            print("⏱️ Propagación DNS: 5-10 minutos")

            # Monitorear propagación automáticamente
            print("\n🔍 Monitoreando propagación DNS...")
            self.monitor_dns_propagation("creator.avermex.com")

            print("\n✅ Verificación completa:")
            print("   nslookup creator.avermex.com")
            print("   curl -I https://creator.avermex.com")

        return result

    def monitor_dns_propagation(self, domain: str, timeout: int = 600) -> bool:
        """
        Monitorear propagación DNS en tiempo real
        """
        start_time = time.time()
        print(f"⏳ Esperando propagación de {domain}...")

        while time.time() - start_time < timeout:
            try:
                # Verificar DNS lookup
                result = subprocess.run(
                    ["nslookup", domain],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 and "aion-creator" in result.stdout:
                    elapsed = int(time.time() - start_time)
                    print(f"✅ DNS propagado exitosamente en {elapsed} segundos")

                    # Verificar HTTP también
                    try:
                        response = requests.get(f"https://{domain}", timeout=10)
                        if response.status_code == 200:
                            print(f"🌐 HTTPS funcionando correctamente")
                            return True
                    except:
                        print(f"⚠️ DNS propagado pero HTTPS aún no disponible")

                    return True

            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                print(f"⚠️ Error verificando DNS: {e}")

            print(".", end="", flush=True)
            time.sleep(15)  # Verificar cada 15 segundos

        print(f"\n⚠️ Timeout después de {timeout//60} minutos")
        return False

    def setup_enterprise_dns(self, domain: str, config: Dict[str, str]) -> Dict[str, Any]:
        """
        Configurar múltiples subdominios para setup enterprise
        """
        print(f"🏢 Configurando DNS enterprise para {domain}...")

        results = {}
        total = len(config)

        for i, (subdomain, target) in enumerate(config.items(), 1):
            print(f"[{i}/{total}] Configurando {subdomain}.{domain} -> {target}")

            result = self.setup_cname(domain, subdomain, target)
            results[subdomain] = result

            if result["success"]:
                print(f"   ✅ {subdomain}.{domain}")
            else:
                print(f"   ❌ Error en {subdomain}.{domain}")

            time.sleep(1)  # Rate limiting

        # Resumen
        successful = sum(1 for r in results.values() if r["success"])
        print(f"\n📊 Configuración completada: {successful}/{total} exitosos")

        return {
            "success": successful == total,
            "results": results,
            "summary": f"{successful}/{total} subdominios configurados"
        }

    def backup_dns_config(self, domain: str) -> Dict[str, Any]:
        """
        Crear backup de configuración DNS
        """
        print(f"💾 Creando backup DNS para {domain}...")

        records_result = self.list_dns_records(domain)
        if not records_result["success"]:
            return records_result

        backup_data = {
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "records": records_result["records"]
        }

        filename = f"dns_backup_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(backup_data, f, indent=2)

            print(f"✅ Backup guardado: {filename}")
            return {
                "success": True,
                "filename": filename,
                "records_count": len(backup_data["records"])
            }
        except Exception as e:
            print(f"❌ Error guardando backup: {e}")
            return {"success": False, "error": str(e)}

    def restore_dns_config(self, backup_file: str) -> Dict[str, Any]:
        """
        Restaurar configuración DNS desde backup
        """
        print(f"🔄 Restaurando DNS desde {backup_file}...")

        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)

            domain = backup_data["domain"]
            records = backup_data["records"]

            print(f"📋 Restaurando {len(records)} registros para {domain}")

            # Restaurar cada registro
            results = []
            for record in records:
                if record["type"] == "CNAME":
                    result = self.setup_cname(
                        domain=domain,
                        subdomain=record["name"],
                        target=record["data"]
                    )
                    results.append(result)

            successful = sum(1 for r in results if r["success"])
            print(f"✅ Restauración completada: {successful}/{len(results)}")

            return {
                "success": successful == len(results),
                "restored": successful,
                "total": len(results)
            }

        except Exception as e:
            print(f"❌ Error restaurando: {e}")
            return {"success": False, "error": str(e)}


def main():
    """
    CLI principal como wrangler
    """
    parser = argparse.ArgumentParser(description='GoDaddy DNS Manager - Como wrangler pero para GoDaddy')

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # Comando para configurar CNAME
    cname_parser = subparsers.add_parser('cname', help='Configurar registro CNAME')
    cname_parser.add_argument('domain', help='Dominio base (ej: avermex.com)')
    cname_parser.add_argument('subdomain', help='Subdominio (ej: creator)')
    cname_parser.add_argument('target', help='Destino (ej: aion-creator.pages.dev)')

    # Comando para listar registros
    list_parser = subparsers.add_parser('list', help='Listar registros DNS')
    list_parser.add_argument('domain', help='Dominio a consultar')

    # Comando para eliminar registro
    delete_parser = subparsers.add_parser('delete', help='Eliminar registro DNS')
    delete_parser.add_argument('domain', help='Dominio')
    delete_parser.add_argument('type', help='Tipo de registro (CNAME, A, etc)')
    delete_parser.add_argument('name', help='Nombre del registro')

    # Comando para configurar creator automáticamente
    subparsers.add_parser('setup-creator', help='Configurar creator.avermex.com automáticamente con monitoring')

    # Comando para verificar dominio
    info_parser = subparsers.add_parser('info', help='Información del dominio')
    info_parser.add_argument('domain', help='Dominio a verificar')

    # Comando para backup DNS
    backup_parser = subparsers.add_parser('backup', help='Crear backup de configuración DNS')
    backup_parser.add_argument('domain', help='Dominio a respaldar')

    # Comando para restaurar DNS
    restore_parser = subparsers.add_parser('restore', help='Restaurar configuración DNS')
    restore_parser.add_argument('backup_file', help='Archivo de backup a restaurar')

    # Comando para setup enterprise
    enterprise_parser = subparsers.add_parser('enterprise-setup', help='Configurar múltiples subdominios enterprise')
    enterprise_parser.add_argument('domain', help='Dominio base')
    enterprise_parser.add_argument('config_file', help='Archivo JSON con configuración de subdominios')

    # Comando para monitoreo DNS
    monitor_parser = subparsers.add_parser('monitor', help='Monitorear propagación DNS')
    monitor_parser.add_argument('domain', help='Dominio a monitorear')
    monitor_parser.add_argument('--timeout', type=int, default=600, help='Timeout en segundos (default: 600)')

    # Comando para setup completo AION
    aion_parser = subparsers.add_parser('setup-aion-complete', help='Setup completo AION con todos los subdominios')

    args = parser.parse_args()

    # Verificar credenciales
    api_key = os.getenv('GODADDY_API_KEY')
    api_secret = os.getenv('GODADDY_API_SECRET')

    if not api_key or not api_secret:
        print("❌ Credenciales no configuradas")
        print("\n📝 Para configurar:")
        print("   1. Ve a https://developer.godaddy.com")
        print("   2. Crea una API key")
        print("   3. Configura variables de entorno:")
        print("      set GODADDY_API_KEY=tu_api_key")
        print("      set GODADDY_API_SECRET=tu_api_secret")
        sys.exit(1)

    # Crear manager
    manager = GoDaddyDNSManager(api_key, api_secret)

    # Ejecutar comando
    if args.command == 'cname':
        result = manager.setup_cname(args.domain, args.subdomain, args.target)
    elif args.command == 'list':
        result = manager.list_dns_records(args.domain)
    elif args.command == 'delete':
        result = manager.delete_record(args.domain, args.type, args.name)
    elif args.command == 'setup-creator':
        result = manager.setup_creator_subdomain()
    elif args.command == 'info':
        result = manager.check_domain_info(args.domain)
    elif args.command == 'backup':
        result = manager.backup_dns_config(args.domain)
    elif args.command == 'restore':
        result = manager.restore_dns_config(args.backup_file)
    elif args.command == 'monitor':
        success = manager.monitor_dns_propagation(args.domain, args.timeout)
        result = {"success": success}
    elif args.command == 'enterprise-setup':
        # Cargar configuración desde archivo JSON
        try:
            with open(args.config_file, 'r') as f:
                config = json.load(f)
            result = manager.setup_enterprise_dns(args.domain, config)
        except Exception as e:
            result = {"success": False, "error": f"Error leyendo archivo: {e}"}
    elif args.command == 'setup-aion-complete':
        # Configuración predefinida para AION
        aion_config = {
            "creator": "aion-creator.pages.dev",
            "api": "aion-creator-api.pako-molina.workers.dev",
            "docs": "aion-docs.pages.dev",
            "admin": "aion-admin.pages.dev",
            "status": "aion-status.pages.dev"
        }
        result = manager.setup_enterprise_dns("avermex.com", aion_config)
    else:
        parser.print_help()
        sys.exit(1)

    # Mostrar resultado
    if result["success"]:
        print(f"\n✅ Operación completada exitosamente")
    else:
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()