# 🔑 Guía Completa: Obtener API Keys de GoDaddy

## 📍 Paso a Paso para Obtener API Keys

### 1. **Accede al Developer Portal**
Ve a: **https://developer.godaddy.com**

### 2. **Inicia Sesión**
- Usa tu cuenta de GoDaddy existente
- Si no tienes cuenta, créala en godaddy.com primero

### 3. **Navega a API Keys**
En el portal, busca la sección **"API Keys"** (icono de llave 🔑)
- O ve directamente a la sección de administración de claves

### 4. **Crear Nueva API Key**
GoDaddy te preguntará sobre el **entorno**:

#### 🧪 **OTE (Test Environment)**
- **Para**: Desarrollo y pruebas
- **URL**: `https://api.ote-godaddy.com/v1`
- **Características**:
  - Cambios NO afectan DNS real
  - Perfecto para probar el CLI
  - Gratis e ilimitado

#### 🚀 **Production Environment**
- **Para**: Cambios DNS reales
- **URL**: `https://api.godaddy.com/v1`
- **Características**:
  - Cambios afectan DNS real
  - Para uso en producción
  - Requiere precaución

### 5. **Configurar en el CLI**

Una vez que tengas tus keys:

#### Para Windows:
```batch
# OTE (Test)
set GODADDY_API_KEY=tu_ote_key
set GODADDY_API_SECRET=tu_ote_secret
set GODADDY_ENVIRONMENT=ote

# Production
set GODADDY_API_KEY=tu_production_key
set GODADDY_API_SECRET=tu_production_secret
set GODADDY_ENVIRONMENT=production
```

#### Para Linux/Mac:
```bash
# OTE (Test)
export GODADDY_API_KEY=tu_ote_key
export GODADDY_API_SECRET=tu_ote_secret
export GODADDY_ENVIRONMENT=ote

# Production
export GODADDY_API_KEY=tu_production_key
export GODADDY_API_SECRET=tu_production_secret
export GODADDY_ENVIRONMENT=production
```

## 🎯 Recomendaciones

### ✅ **Empezar con OTE**
1. Obtén keys de **OTE** primero
2. Prueba todos los comandos del CLI
3. Familiarízate con la herramienta
4. **DESPUÉS** obtén keys de Production

### 🔒 **Para Production**
- Usa keys de Production solo cuando estés seguro
- Haz backup de DNS antes de cambios importantes
- Prueba primero en OTE

## 🛠️ **Comandos de Prueba**

### Con OTE:
```bash
# Probar conexión
python GODADDY_AUTO_SETUP.py info example.com

# Configurar test
python GODADDY_AUTO_SETUP.py cname example.com test aion-creator.pages.dev
```

### Con Production:
```bash
# Configurar creator.avermex.com real
python GODADDY_AUTO_SETUP.py setup-creator
```

## ❓ **Troubleshooting**

### **No encuentro "API Keys"**
- Asegúrate de estar logueado
- Busca un icono de llave 🔑
- O busca "Keys" en el portal

### **Error 401 Unauthorized**
- Verifica API Key y Secret
- Confirma el entorno (OTE vs Production)
- Refresca las variables de entorno

### **Error 403 Forbidden**
- Confirma que el dominio esté en tu cuenta
- Verifica permisos de la API key

## 🌐 **URLs Importantes**

- **Developer Portal**: https://developer.godaddy.com
- **API Documentation**: https://developer.godaddy.com/doc
- **OTE API**: https://api.ote-godaddy.com/v1
- **Production API**: https://api.godaddy.com/v1

## 💡 **Tips Pro**

1. **Separar Entornos**: Usa diferentes keys para test y production
2. **Backup**: Siempre haz backup antes de cambios masivos
3. **Monitoreo**: Usa el comando `monitor` para verificar cambios
4. **Documentación**: Lee la doc oficial para casos avanzados

¡Ya puedes usar el CLI de forma segura! 🚀