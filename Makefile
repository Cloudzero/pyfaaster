# Copyright (c) 2017 CloudZero - ALL RIGHTS RESERVED - PROPRIETARY AND CONFIDENTIAL
# Unauthorized copying of this file and/or project, via any medium is strictly prohibited.
# Direct all questions to legal@cloudzero.com


NAME ?= pyfaaster

ERROR_COLOR = \033[1;31m
INFO_COLOR = \033[1;32m
WARN_COLOR = \033[1;33m
NO_COLOR = \033[0m

.PHONY: init build test
default: test

#################
#
# Helper Targets
#
#################
# Add an implicit guard for parameter input validation; use as target dependency guard-VARIABLE_NAME, e.g. guard-AWS_ACCESS_KEY_ID
guard-%:
	@if [ "${${*}}" = "" ]; then \
		printf \
			"$(ERROR_COLOR)ERROR:$(NO_COLOR) Variable [$(ERROR_COLOR)$*$(NO_COLOR)] not set.\n"; \
		exit 1; \
	fi


help:                                    ## Prints the names and descriptions of available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


#################
#
# Docker Targets
#
#################
check-docker:                            ## Exits if docker is not installed and available
	@if which docker &>/dev/null ; then \
		printf "$(INFO_COLOR)OK:$(NO_COLOR) docker found on path!\n" ; \
	else \
		printf "$(ERROR_COLOR)ERROR:$(NO_COLOR) docker not found on path. Please install and configure docker!\n" ; \
		exit 1 ; \
	fi


#################
#
# Python Targets
#
#################
init:                                    ## ensures all dev dependencies into the current virtualenv
	@if [[ "$$VIRTUAL_ENV" = "" ]] ; then printf "$(WARN_COLOR)WARN:$(NO_COLOR) No virtualenv found, install dependencies globally." ; fi
	pip install -r requirements-dev.txt


test: check-docker                       ## runs the unit tests on all available python runtimes
	@tox


lint:                                    ## lints the code via adherence to PEP8 standards
	flake8


lint-fix:								                 ## fixes the code in place so that it will pass `make lint`
	autopep8 --ignore E265,E266,E402 --in-place --recursive --max-line-length=120 --exclude vendored .


clean-pyc:                               ## rms pyc, pyo, *~, and __pycache__
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +


build: test                              ## builds sdist bdist_wheel
	./setup.py sdist bdist_wheel --universal


upload: build                            ## twine uploads dist/*
	twine upload dist/*


#################
#
# Serverless Framework Targets
#
#################
SLS_PLUGINS = serverless-dynamodb-autoscaling serverless-prune-plugin
check-sls:                               ## yarn installs so that sls plugins are available
	yarn install

# neat trick so that vendor target only runs when requirements.txt is newer than vendored folder
VENDORED_FOLDER := vendored
.PHONY: vendor
vendor: $(VENDORED_FOLDER) check-docker
$(VENDORED_FOLDER): requirements.txt    ## install requirements into $(VENDORED_FOLDER) when requirements.txt is newer than the folder
	rm -rf $(VENDORED_FOLDER)
	docker run -it -v $(shell pwd):/pyfaaster lambci/lambda:build-python3.6 /bin/sh -c "pip install -r /pyfaaster/requirements.txt -t /pyfaaster/vendored/"


sls_help:                                ## print help for make (deploy|remove) targets
	@printf "\nmake (deploy|remove)\n"
	@printf "Usage:\n"
	@printf "    make stage=<namespace> [profile=<aws-profle>] [environment=(dev|staging|prod)] deploy\n"
	@printf "\n"
	@printf "Required:\n"
	@printf "    stage:       stage aka \"namespace\", so you can install multiple stacks in same account.\n"
	@printf "\n"
	@printf "Optional:\n"
	@printf "    profile:     aws profile used for credentials, needed if you don't set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or AWS_DEFAULT_PROFILE env vars \n"
	@printf "    environment: indicates the general environment being used needed if you don't set WEB_DEFAULT_ENVIRONMENT.  One of (dev|staging|prod) \n"


sls: guard-action                        ## run sls with given stage and environment
	@if [ -z "$${stage}" ] && [ -z "$${environment}" ]; then make guard-stage ; make guard-environment ; make sls_help ; exit 1 ; fi
	@if [ -n "$${AWS_ACCESS_KEY_ID}" -a -n "$${AWS_SECRET_ACCESS_KEY}" ] ; then \
		printf "$(WARN_COLOR)WARN:$(NO_COLOR) Found AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY vars, using those for sls "$${action}".\n" ; \
			sls "$${action}" --stage=$${stage} --environment=$${environment} ; \
		elif [ -n "$${AWS_DEFAULT_PROFILE}" ] ; then \
			printf "$(WARN_COLOR)WARN:$(NO_COLOR) Found AWS_DEFAULT_PROFILE var, using it for sls "$${action}".\n" ; \
			sls "$${action}" --stage=$${stage} --environment=$${environment} --aws-profile=$${AWS_DEFAULT_PROFILE} ; \
		elif [ -n "$${profile}" ] ; then \
			printf "$(WARN_COLOR)WARN:$(NO_COLOR) Found 'profile=$${profile}' argument, using it for sls "$${action}".\n" ; \
			sls "$${action}" --stage=$${stage} --environment=$${environment} --aws-profile=$${profile} ; \
		elif [ -z "$${profile}" ] ; then \
			printf "$(WARN_COLOR)WARN:$(NO_COLOR) No AWS profile specified, using default.\n" ; \
			sls "$${action}" --stage=$${stage} --environment=$${environment} ; \
		else  \
			printf "$(ERROR_COLOR)ERROR:$(NO_COLOR) No AWS credentials found or passed.\n" ; \
			make sls_help ; \
			exit 1 ; \
		fi


.PHONY: deploy
deploy: check-sls vendor                 ## wrap sls deploy
	@make action=deploy sls
