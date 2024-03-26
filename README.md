# Airport-Bot-GenerativeAI
GenerativeAI chatbot framework for Airports. This bot can provide all sorts of information which is publically available on the websites.
## Run Locally
Clone the project
```bash
  git clone https://github.com/ASUCICREPO/Airport-Bot-genAI.git
```
Go to the project directory
```bash
  cd Airport-Bot-genAI/cdk-typescript
```
Install `Typescript` and then `aws-cdk`
```bash
  npm -g install typescript
  npm -g install aws-cdk
```
Verify cdk installation by
```bash
  cdk --version
```
Install dependencies
```bash
  npm install
```
Enter Account, Region Information in `bin/cdk-typescript.ts`
```bash
  env: { account: '', region: '' }
```
Check that your system has access to make AWS calls , then run the cdk stack.

**kendraIndexId**: Index which has a crawler data source which will crawl the website and indexes the content. **Optional**

**website**: website link which will be added in the data source if not already provided otherwise in a disclaimer for users. **Mandatory**

**page_title**: Set page title of the frontend. **Mandatory**
```bash
  cdk synth --context kendraIndexId=123456677890 --context website='abc.com' --context page_title='Phoenix Airport Bot'
  cdk deploy --context kendraIndexId=123456677890 --context website='abc.com' --context page_title='Phoenix Airport Bot'
```
