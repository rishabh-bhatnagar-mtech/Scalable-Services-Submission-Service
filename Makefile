build_submission_image:
	docker build -t submission-service:0.0.2 . -f deployments/Dockerfile

build_consumer_image:
	docker build -t consumer-service:0.0.3 . -f deployments/consumer.Dockerfile

delete_prev_deployment:
	kubectl delete deployment submission-service -n submission-service || true

deploy_k8s:
	kubectl apply -f deployments/namespace.yaml
	kubectl apply -f deployments/kafka.yaml
	kubectl apply -f deployments/db.yaml
	kubectl apply -f deployments/submission_service.yaml
	kubectl apply -f deployments/consumer_service.yaml

deploy: delete_prev_deployment build_consumer_image build_submission_image deploy_k8s
