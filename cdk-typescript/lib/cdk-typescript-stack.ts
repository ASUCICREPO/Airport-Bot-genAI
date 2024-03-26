import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as kendra from 'aws-cdk-lib/aws-kendra';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { DockerImageAsset } from 'aws-cdk-lib/aws-ecr-assets';
import {bedrock} from '@cdklabs/generative-ai-cdk-constructs';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs_patterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';


export class CdkTypescriptStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    //Run-time Context
    let indexId = this.node.tryGetContext('kendraIndexId') ?? '';
    const website = this.node.tryGetContext('website') ?? '';
    const page_title = this.node.tryGetContext('page_title') ?? '';

    if (indexId == '') {
      
      const kendra_index_role = this.create_kendra_index_role()
      //Create Kendra Index
      const kendraIndex = new kendra.CfnIndex(this, 'airport-bot-index-ts', {
        edition: 'DEVELOPER_EDITION',
        name: 'airport-bot-kendra-index',
        roleArn: kendra_index_role,
      });

      //Create a webcrawler data source and attach to above index
      const crawler_data_source = new kendra.CfnDataSource(this, 'airport-bot-crawler-data-source-ts', {
        indexId: kendraIndex.attrId,
        name: 'airport-bot-crawler-data-source',
        type: 'WEBCRAWLER',
        description: 'Crawler settings in Airport website, will be indexed by kendra',
        roleArn: kendra_index_role,
        dataSourceConfiguration:{
          webCrawlerConfiguration:{
            urls:{
              seedUrlConfiguration:{
                seedUrls: [website],
                webCrawlerMode: 'EVERYTHING'
              }
            },
            crawlDepth: 2
          }
        },
      });
      crawler_data_source.schedule = '00***'
      crawler_data_source._addResourceDependency(kendraIndex)
      indexId = kendraIndex.attrId;
    }

    //Create an IAM role for Lambda function
    const lambda_role = this.create_lambda_role()

    //Create a Lambda function
    const lambda_function = new lambda.Function(this, 'airport-bot-lambda-ts', {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_12,
      code: cdk.aws_lambda.Code.fromAsset('../aws-Airport-Bot/Airport-Bot-Lambda'),
      handler: 'index.lambda_handler',
      role: lambda_role,
      environment: {
        "KENDRA_INDEX_ID": indexId
      },
      memorySize: 3008,
      timeout: cdk.Duration.seconds(60),
      description: "This lambda function ask Kendra or Make API requests to JFK Airport website",
      ephemeralStorageSize: cdk.Size.mebibytes(1000),
      functionName: 'airport-bot-lambda-action-group'
    
      });

    // Creating Bedrock Agent
    const agent = new bedrock.Agent(this, 'airport-bot-agent-ts', {
      name: 'airport-bot-bedrock-agent',
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_INSTANT_V1_2,
      instruction: 'You are equipped with comprehensive data pertaining to John F. Kennedy International Airport (JFK) which is an International airport in New York, United States. Your primary objective is to respond to all queries in a professional manner, adopting the perspective of an individual situated at a window within JFK Airport. Check if the information being requested is for JFK airport, answer only if the information is related to the JFK airport, It is imperative that you refrain from addressing any inquiries unrelated to JFK Airport. You are only supposed to request the answer from your action group. You engage with people from all background so make sure you respond in a way everyone understand.',
      idleSessionTTL: cdk.Duration.minutes(15),
      shouldPrepareAgent: true,
      description: 'Agent which can answers all the questions about JFK airport.',
      aliasName: 'v1'
    });

    //Adding action group to agent
    agent.addActionGroup({
      actionGroupName: 'airport-bot-action-group',
      actionGroupExecutor: lambda_function,
      actionGroupState: "ENABLED",
      apiSchema: bedrock.ApiSchema.fromAsset('../api-doc/aws_bedrock_agent_openapi.json')
    });

    // Frontend Container Image code
    const asset = new DockerImageAsset(this, 'Airport-Bot-Image', {
      directory: "../streamlit-app",
    });

    //VPC for the frontend
    const vpc = new ec2.Vpc(this, 'VPC', {
      vpcName: 'Airport-Bot-cdk-VPC',
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Web',
          subnetType: ec2.SubnetType.PUBLIC,
        },],
      
    });
    
    //ECS Cluster
    const cluster = new ecs.Cluster(this, 'ECS-Cluster', {
      vpc
    });

    //Frontend for container-node
    const securityGroup = new ec2.SecurityGroup(this, 'Airport-Bot-SG', {
      vpc: vpc,
      securityGroupName: 'Airport-Bot-sg',
      description: 'Allow HTTP and HTTPS traffic',
      allowAllOutbound: true
    })
    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80))
    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443))
    securityGroup.addEgressRule(ec2.Peer.anyIpv4(), ec2.Port.allTraffic())
    
    //Fargate Service - Load Balancer
    const loadBalancedService = new ecs_patterns.ApplicationLoadBalancedFargateService(this, 'Fargate-service',{
      cluster,
      taskImageOptions: {
        image: ecs.ContainerImage.fromRegistry(asset.imageUri),
        environment: {
          AGENT_ID: agent.agentId,
          AGENT_ALIAS_ID: agent.aliasId ?? '',
          PAGE_TITLE: page_title,
          WEBSITE: website,
        },
        containerPort: 8501,
        enableLogging: true,
        
      },
      cpu: 4096,
      ephemeralStorageGiB: 21,
      memoryLimitMiB: 8192,
      securityGroups: [securityGroup],
      assignPublicIp: true,
      publicLoadBalancer: true,
      desiredCount: 1,
      targetProtocol: cdk.aws_elasticloadbalancingv2.ApplicationProtocol.HTTP,
    });

    
    const pl1 = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['ecr:GetAuthorizationToken','ecr:BatchCheckLayerAvailability', 'ecr:GetDownloadUrlForLayer', 'ecr:BatchGetImage'],
      resources: ['*'],
    })
    loadBalancedService.service.taskDefinition.executionRole?.addToPrincipalPolicy(pl1);

    const pl2 = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['bedrock:InvokeAgent'],
      resources: [agent.aliasArn ?? '']//[alias.aliasArn]
    })
    loadBalancedService.service.taskDefinition.taskRole.addToPrincipalPolicy(pl2);
  

  // Cloud-Front Distribution
  const cloudFrontCachePolicy = new cloudfront.CfnCachePolicy(this, 'CloudFrontCachePolicy', {
    cachePolicyConfig: {
      comment: 'Policy with caching disabled',
      minTtl: 0,
      maxTtl: 0,
      parametersInCacheKeyAndForwardedToOrigin: {
        queryStringsConfig: {
          queryStringBehavior: 'none',
        },
        enableAcceptEncodingBrotli: false,
        headersConfig: {
          headerBehavior: 'none',
        },
        cookiesConfig: {
          cookieBehavior: 'none',
        },
        enableAcceptEncodingGzip: false,
      },
      defaultTtl: 0,
      name: 'CachingDisabled',
    },
  });
  cloudFrontCachePolicy.cfnOptions.deletionPolicy = cdk.CfnDeletionPolicy.DELETE;

  const cloudFrontReqPolicy = new cloudfront.CfnOriginRequestPolicy(this, 'CloudFrontOriginRequestPolicy', {
    originRequestPolicyConfig: {
      queryStringsConfig: {
        queryStringBehavior: 'all',
      },
      comment: 'Policy to forward all parameters in viewer requests',
      headersConfig: {
        headerBehavior: 'allViewer',
      },
      cookiesConfig: {
        cookieBehavior: 'all',
      },
      name: 'AllViewer',
    },
  });
  cloudFrontReqPolicy.cfnOptions.deletionPolicy = cdk.CfnDeletionPolicy.DELETE;

  const cloudFrontDist = new cloudfront.CfnDistribution(this, 'CloudFrontDistribution', {
    distributionConfig: {
      logging: {
        includeCookies: false,
        bucket: '',
        prefix: '',
      },
      comment: '',
      defaultRootObject: '',
      origins: [
        {
          connectionTimeout: 10,
          originAccessControlId: '',
          connectionAttempts: 3,
          originCustomHeaders: [
          ],
          domainName: loadBalancedService.loadBalancer.loadBalancerDnsName,
          originShield: {
            enabled: false,
          },
          originPath: '',
          id: loadBalancedService.loadBalancer.loadBalancerDnsName,
          customOriginConfig: {
            originKeepaliveTimeout: 5,
            originReadTimeout: 30,
            originSslProtocols: [
              'SSLv3',
              'TLSv1',
              'TLSv1.1',
              'TLSv1.2',
            ],
            httpsPort: 443,
            httpPort: 80,
            originProtocolPolicy: 'http-only',
          },
        },
      ],
      viewerCertificate: {
        minimumProtocolVersion: 'TLSv1',
        cloudFrontDefaultCertificate: true,
      },
      priceClass: 'PriceClass_100',
      defaultCacheBehavior: {
        compress: false,
        functionAssociations: [
        ],
        lambdaFunctionAssociations: [
        ],
        targetOriginId: loadBalancedService.loadBalancer.loadBalancerDnsName,
        viewerProtocolPolicy: 'redirect-to-https',
        trustedSigners: [
        ],
        fieldLevelEncryptionId: '',
        trustedKeyGroups: [
        ],
        allowedMethods: [
          'HEAD',
          'DELETE',
          'POST',
          'GET',
          'OPTIONS',
          'PUT',
          'PATCH',
        ],
        cachedMethods: [
          'HEAD',
          'GET',
          'OPTIONS',
        ],
        smoothStreaming: false,
        originRequestPolicyId: cloudFrontReqPolicy.ref,
        cachePolicyId: cloudFrontCachePolicy.ref,
      },
      staging: false,
      customErrorResponses: [
      ],
      continuousDeploymentPolicyId: '',
      originGroups: {
        quantity: 0,
        items: [
        ],
      },
      enabled: true,
      aliases: [
      ],
      ipv6Enabled: true,
      webAclId: '',
      httpVersion: 'http2and3',
      restrictions: {
        geoRestriction: {
          locations: [
          ],
          restrictionType: 'none',
        },
      },
      cacheBehaviors: [
      ],
    },
  });
  cloudFrontDist.cfnOptions.deletionPolicy = cdk.CfnDeletionPolicy.DELETE;

  new cdk.CfnOutput(this, 'Cloud-Front-Domain', {
    value: cloudFrontDist.attrDomainName
  });
  }

  /////////////////////////////////////////////////////////////////////////////////////////////
  //Create an IAM role for kendra index
  create_kendra_index_role(): string {
    const kendra_index_role = new iam.Role(this, 'airport-bot-kendra-index-role', {
      assumedBy: new cdk.aws_iam.ServicePrincipal('kendra.amazonaws.com'),
    })

    const kendraIndexPolStat1 = new cdk.aws_iam.PolicyStatement({
      effect: cdk.aws_iam.Effect.ALLOW,
      actions: ['cloudwatch:PutMetricData'],
      resources: ['*'],
    })

    const kendraIndexPolStat2 = new cdk.aws_iam.PolicyStatement({
      effect: cdk.aws_iam.Effect.ALLOW,
      actions: ['logs:DescribeLogGroups'],
      resources: ['*']
    });

    //const roleFormat1 = `arn:aws:logs:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:log-group:/aws/kendra/*`;
    const kendraIndexPolStat3 = new cdk.aws_iam.PolicyStatement({
      effect: cdk.aws_iam.Effect.ALLOW,
      actions: ['logs:CreateLogStream'],
      resources: ['*']
    });

    //const roleFormat2 = `arn:aws:logs:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:log-group:/aws/kendra/*:log-stream:*`;
    const kendraIndexPolStat4 = new cdk.aws_iam.PolicyStatement({
      effect: cdk.aws_iam.Effect.ALLOW,
      actions: ['logs:PutLogEvents', 'logs:CreateLogGroup', 'logs:DescribeLogStreams'],
      resources: ['*']
    });

    const kendraIndexPolStat5 = new cdk.aws_iam.PolicyStatement({
      effect: cdk.aws_iam.Effect.ALLOW,
      actions: ['kendra:BatchPutDocument'],
      resources: ['*']
    });

    kendra_index_role.addToPolicy(kendraIndexPolStat1)
    kendra_index_role.addToPolicy(kendraIndexPolStat2)
    kendra_index_role.addToPolicy(kendraIndexPolStat3)
    kendra_index_role.addToPolicy(kendraIndexPolStat4)
    kendra_index_role.addToPolicy(kendraIndexPolStat5)

    return kendra_index_role.roleArn;
  }

  //////////////////////////////////////////////////////////////////////////////////////////////////////////
  //Create an IAM role for Lambda function
  create_lambda_role(): iam.Role {
   const lambda_role = new iam.Role(this, 'airport-bot-lambda-role', {
     assumedBy: new cdk.aws_iam.ServicePrincipal('lambda.amazonaws.com'),
   })

  // Policy Statement 1
  const lambdaPolStat1 = new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: ['logs:CreateLogGroup'],
    resources: ['*']
  });

  // Policy Statement 2
  const lambdaPolStat2 = new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: ['logs:CreateLogStream', 'logs:PutLogEvents'],
    resources: ['*'],
    conditions: {
      StringEquals: {
        'logs:ResourceTag/aws:cloudformation:stack-name': 'CdkAirportBotStack'
      }
    }
  });

  // Policy Statement 3
  const lambdaPolStat3 = new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: ['kendra:Query','kendra:DescribeDataSource'],
    resources: ['*']
  });

  // Add the Policy statements to the Role
  lambda_role.addToPolicy(lambdaPolStat1);
  lambda_role.addToPolicy(lambdaPolStat2);
  lambda_role.addToPolicy(lambdaPolStat3);

   return lambda_role;
  }

}