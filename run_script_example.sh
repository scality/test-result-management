#!/bin/sh
# ensure you filled up every variable in here :

# url to the artifact listing
ARTIFACT_URL="https://eve.devsca.com/github/scality/cloudserver/artifacts/builds/"

# url to upload artifact datas
ELASTICSEARCH_URL="https://mon.scality.net/elastic/"

# artifact to be uploaded
ARTIFACT="github%3Ascality%3Acloudserver%3Astaging-7.5.1.r210802200751.62e66dad.pre-merge.00014189/"

# username and password for elastic and artifact
# if there is no login/password needed, you sould removed them from the command line below
ARTIFACT_USERNAME=""
ARTIFACT_PASSWORD=""
ELASTICSEARCH_USERNAME=""
ELASTICSEARCH_PASSWORD=""

# settings for the script, it's a json file with some required field, refeer to README
SETTING_FILE="cloudserver.json"

. venv/bin/activate

python transfer_artifact_to_ES.py \
			  ${ARTIFACT_URL} \
			  ${ELASTICSEARCH_URL} \
			  ${SETTING_FILE} \
              --artifact .*${ARTIFACT}.* \
	          --artifact-username ${ARTIFACT_USERNAME} \
	          --artifact-password ${ARTIFACT_PASSWORD} \
	          --elastic-username ${ELASTICSEARCH_USERNAME} \
	          --elastic-password ${ELASTICSEARCH_PASSWORD} \
              --soft-fail