# Airport-Bot-GenerativeAI

GenerativeAI chatbot framework for Airports. This bot can provide all sorts of information which is publically available on the websites.

## Run Locally

Clone the project

```bash {"id":"01HTZEMSE9DJB4D5JMBQWRGP9B"}
  git clone https://github.com/ASUCICREPO/Airport-Bot-genAI.git
```

Go to the project directory

```bash {"id":"01HTZEMSE9DJB4D5JMBTGRZWT1"}
  cd Airport-Bot-genAI/cdk-typescript
```

Install `Typescript` and then `aws-cdk`

```bash {"id":"01HTZEMSE9DJB4D5JMBWK9G9FA"}
  npm -g install typescript
  npm -g install aws-cdk
```

Verify cdk installation by

```bash {"id":"01HTZEMSE9DJB4D5JMBZ3AMSRG"}
  cdk --version
```

Install dependencies

```bash {"id":"01HTZEMSE9DJB4D5JMBZR4V1NW"}
  npm install
```

Check that your system has access to make AWS calls , then run the cdk stack.

**kendraIndexId**: Index which has a crawler data source which will crawl the website and indexes the content. **Optional**

**website**: website link which will be added in the data source if not already provided otherwise in a disclaimer for users. **Mandatory**

__page_title__: Set page title of the frontend. __Mandatory__

```bash {"id":"01HTZEMSE9DJB4D5JMC5ZBZ80K"}
  cdk synth --context kendraIndexId=123456677890 --context website='abc.com' --context page_title='Phoenix Airport Bot'
  cdk deploy --context kendraIndexId=123456677890 --context website='abc.com' --context page_title='Phoenix Airport Bot'
```
