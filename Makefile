create_submission_image:
	docker build -t submission-service:0.0.1 -f deployments/Dockerfile .

deploy_k8s:
	kubectl apply -f deployments/namespace.yaml
	kubectl apply -f deployments/kafka.yaml
	kubectl apply -f deployments/submission_service.yaml

deploy: create_submission_image deploy_k8s
