V=@
VERSION=$(shell bash -c "if which python3 > /dev/null 2>&1; then python3 version.py; else python version.py; fi")

DOCKER_IMAGE_NAME=artifact-to-es
DOCKER_REPOSITORY=test_tools
DOCKER_REGISTRY=registry.scality.com
DOCKER_IMAGE_TAG=$(DOCKER_REGISTRY)/$(DOCKER_REPOSITORY)/$(DOCKER_IMAGE_NAME):$(VERSION)

.PHONY default:
default:
	$(V)echo "Use 'make release' to release the build to ${DOCKER_REGISTRY}"
	$(V)echo "Use 'make build' to build ${DOCKER_IMAGE_TAG}"

.PHONY: build
build: docker-build

.PHONY: release
release: docker-push

.PHONY: docker-push
docker-push: check-docker-release docker-build
	docker push $(DOCKER_IMAGE_TAG)
	$(V)echo 'Docker image has been released'

.PHONY: docker-build
docker-build:
	docker build . -t $(DOCKER_IMAGE_TAG)
	$(V)echo 'Docker image has been built'

.PHONY: check-docker-release
check-docker-release:
	$(eval DOCKER_RELEASE=$(shell docker pull $(DOCKER_IMAGE_TAG) > /dev/null 2>&1 ; echo $$?))
	$(V)if [ "$(DOCKER_RELEASE)" -eq "0" ]; then \
		echo "Docker image ${DOCKER_IMAGE_TAG} has already been released, maybe you need to change VERSION" ; \
		echo "exitting" ; \
		exit 1 ; \
	fi

