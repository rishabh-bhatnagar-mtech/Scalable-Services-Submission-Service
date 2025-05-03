deploy:
	kubectl apply -f deployments/namespace.yaml
	kubectl apply -f deployments/kafka.yaml
	kubectl apply -f deployments/submission_service.yaml
