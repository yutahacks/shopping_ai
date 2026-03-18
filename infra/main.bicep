@description('Location for all resources')
param location string = resourceGroup().location

@description('Environment name (used as prefix)')
param envName string = 'shopping-ai'

@description('Home IP address for App Gateway allowlist (e.g. 1.2.3.4)')
param homeIpAddress string

@description('OpenAI API key')
@secure()
param openaiApiKey string

// Deploy VNet
module vnet 'vnet.bicep' = {
  name: 'vnet'
  params: {
    location: location
    envName: envName
  }
}

// Deploy Container Apps
module containerApps 'container-app.bicep' = {
  name: 'containerApps'
  params: {
    location: location
    envName: envName
    acaSubnetId: vnet.outputs.acaSubnetId
    openaiApiKey: openaiApiKey
  }
}

output frontendUrl string = containerApps.outputs.frontendUrl
output backendUrl string = containerApps.outputs.backendUrl
