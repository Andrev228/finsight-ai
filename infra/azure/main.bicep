targetScope = 'resourceGroup'

@description('Globally unique prefix for Azure resources.')
param namePrefix string
param location string = resourceGroup().location
param backendImage string
param frontendImage string
param containerRegistryServer string
@secure()
param containerRegistryUsername string
@secure()
param containerRegistryPassword string
@secure()
param postgresAdminPassword string
@secure()
param plaidSecret string
@secure()
param plaidEncryptionKey string
@secure()
param geminiApiKey string
@secure()
param jwtSecret string
@secure()
param adminApiKey string
@secure()
param stripeSecretKey string
@secure()
param stripeWebhookSecret string
param stripePriceId string
param plaidClientId string

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs'
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: '${namePrefix}-postgres'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: 'finsightadmin'
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'finsight'
}

resource postgresExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: postgres
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR'
    source: 'user-override'
  }
}

resource postgresAzureAccess 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource redis 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-redis'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 6379
        transport: 'tcp'
      }
    }
    template: {
      containers: [
        {
          name: 'redis'
          image: 'redis:7-alpine'
          command: ['redis-server']
          args: ['--save', '', '--appendonly', 'no', '--maxmemory', '128mb', '--maxmemory-policy', 'allkeys-lru']
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

var databaseUrl = 'postgresql://finsightadmin:${uriComponent(postgresAdminPassword)}@${postgres.properties.fullyQualifiedDomainName}:5432/finsight?sslmode=require'
var redisUrl = 'redis://${redis.properties.configuration.ingress.fqdn}:6379/0'

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: containerRegistryServer
          username: containerRegistryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        { name: 'registry-password', value: containerRegistryPassword }
        { name: 'database-url', value: databaseUrl }
        { name: 'plaid-secret', value: plaidSecret }
        { name: 'plaid-encryption-key', value: plaidEncryptionKey }
        { name: 'gemini-key', value: geminiApiKey }
        { name: 'jwt-secret', value: jwtSecret }
        { name: 'admin-key', value: adminApiKey }
        { name: 'stripe-secret', value: stripeSecretKey }
        { name: 'stripe-webhook-secret', value: stripeWebhookSecret }
      ]
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'api'
          image: backendImage
          env: [
            { name: 'APP_ENV', value: 'production' }
            { name: 'FRONTEND_ORIGIN', value: 'https://${web.properties.configuration.ingress.fqdn}' }
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'REDIS_URL', value: redisUrl }
            { name: 'PLAID_CLIENT_ID', value: plaidClientId }
            { name: 'PLAID_SECRET', secretRef: 'plaid-secret' }
            { name: 'APP_ENCRYPTION_KEY', secretRef: 'plaid-encryption-key' }
            { name: 'GEMINI_API_KEY', secretRef: 'gemini-key' }
            { name: 'AUTH_JWT_SECRET', secretRef: 'jwt-secret' }
            { name: 'ADMIN_API_KEY', secretRef: 'admin-key' }
            { name: 'STRIPE_SECRET_KEY', secretRef: 'stripe-secret' }
            { name: 'STRIPE_WEBHOOK_SECRET', secretRef: 'stripe-webhook-secret' }
            { name: 'STRIPE_PRICE_ID', value: stripePriceId }
            { name: 'STRIPE_SUCCESS_URL', value: 'https://${web.properties.configuration.ingress.fqdn}/?billing=success' }
            { name: 'STRIPE_CANCEL_URL', value: 'https://${web.properties.configuration.ingress.fqdn}/?billing=cancelled' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/ready', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http'
            http: { metadata: { concurrentRequests: '50' } }
          }
        ]
      }
    }
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-web'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: containerRegistryServer
          username: containerRegistryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        { name: 'registry-password', value: containerRegistryPassword }
      ]
      ingress: {
        external: true
        targetPort: 3000
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'web'
          image: frontendImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

output apiUrl string = 'https://${api.properties.configuration.ingress.fqdn}'
output webUrl string = 'https://${web.properties.configuration.ingress.fqdn}'
output postgresHost string = postgres.properties.fullyQualifiedDomainName
