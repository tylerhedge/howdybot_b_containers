# Shortcuts so nobody has to remember buildx flags.  `make help` lists them.
IMAGE      ?= ghcr.io/change_me/howdybot
ROBOT_BASE ?= nvcr.io/nvidia/cuda:13.0.0-runtime-ubuntu24.04
DOCKERFILE := docker/Dockerfile

.PHONY: help dev shell robot-local robot-test robot-push deploy logs

help:          ## Show this list
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

dev:           ## Build + start the dev container (without VS Code)
	docker compose --profile dev up -d --build dev

shell:         ## Open a shell in the running dev container
	docker compose exec dev bash

robot-local:   ## Build the arm64 ROBOT image on your laptop (via QEMU) for testing
	docker buildx build --platform linux/arm64 --target runtime \
	  --build-arg BASE_IMAGE=$(ROBOT_BASE) -f $(DOCKERFILE) -t howdybot:robot-arm64 --load .

robot-test:    ## Run the arm64 robot image under emulation (no GPU) — proves it launches
	docker run --rm -it --platform linux/arm64 howdybot:robot-arm64

robot-push:    ## Build + push the robot image yourself (normally CI does this)
	docker buildx build --platform linux/arm64 --target runtime \
	  --build-arg BASE_IMAGE=$(ROBOT_BASE) -f $(DOCKERFILE) -t $(IMAGE):robot --push .

deploy:        ## On the Jetson: pull the newest image and restart
	docker compose pull robot && docker compose up -d robot

logs:          ## On the Jetson: follow robot logs
	docker compose logs -f robot
