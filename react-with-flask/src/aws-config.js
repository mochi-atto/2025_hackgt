// AWS Amplify Configuration (v6 format) - Hosted UI
const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-east-2_1QVpsNMpo',
      userPoolClientId: '2v7frs8eeard997vkfaq1smslt', 
      region: 'us-east-2',
      loginWith: {
        oauth: {
          domain: 'us-east-21qvpsnmpo.auth.us-east-2.amazoncognito.com',
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: ['http://localhost:5173/'],
          redirectSignOut: ['http://localhost:5173/'],
          responseType: 'code'
        }
      }
    }
  }
};

export default awsConfig;
