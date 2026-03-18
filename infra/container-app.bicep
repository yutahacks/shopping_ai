@description('Location for all resources')
param location string

@description('Environment name prefix')
param envName string

@description('ACA subnet ID')
param acaSubnetId string

@description('OpenAI API key')
@secure()
param openaiApiKey string

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${envName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: replace('${envName}data', '-', '')
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  name: '${storageAccount.name}/default/data'
}

resource acaEnvironment 'Microsoft.App/managedEnvironments@2023-08-01-preview' = {
  name: '${envName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: acaSubnetId
      internal: true
    }
  }
}

resource storageMount 'Microsoft.App/managedEnvironments/storages@2023-08-01-preview' = {
  name: 'data-storage'
  parent: acaEnvironment
  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: 'data'
      accessMode: 'ReadWrite'
    }
  }
}

resource backendApp 'Microsoft.App/containerApps@2023-08-01-preview' = {
  name: '${envName}-backend'
  location: location
  properties: {
    managedEnvironmentId: acaEnvironment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8000
      }
    }
    template: {
      volumes: [
        {
          name: 'data-volume'
          storageName: storageMount.name
          storageType: 'AzureFile'
        }
      ]
      containers: [
        {
          name: 'backend'
          image: 'ghcr.io/yourorg/shopping-ai-backend:latest'
          env: [
            {
              name: 'OPENAI_API_KEY'
              value: openaiApiKey
            }
            {
              name: 'DATA_DIR'
              value: '/data'
            }
          ]
          volumeMounts: [
            {
              volumeName: 'data-volume'
              mountPath: '/data'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2023-08-01-preview' = {
  name: '${envName}-frontend'
  location: location
  properties: {
    managedEnvironmentId: acaEnvironment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 3000
      }
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: 'ghcr.io/yourorg/shopping-ai-frontend:latest'
          env: [
            {
              name: 'NEXT_PUBLIC_API_URL'
              value: 'http://${backendApp.name}'
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
        maxReplicas: 2
      }
    }
  }
}

output frontendUrl string = frontendApp.properties.configuration.ingress.fqdn
output backendUrl string = backendApp.properties.configuration.ingress.fqdn
