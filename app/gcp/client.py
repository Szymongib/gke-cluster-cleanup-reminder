import googleapiclient.discovery


def list_clusters(gcp_project):
    container = googleapiclient.discovery.build('container', 'v1')

    cluster_list_response = container.projects().locations().clusters().list(
        parent=f"projects/{gcp_project}/locations/-").execute()

    return cluster_list_response["clusters"]


def delete_cluster(gcp_project, cluster):
    container = googleapiclient.discovery.build('container', 'v1')

    params = cluster.split("/")
    location = params[0]
    name = params[1]

    delete_response = container.projects().locations().clusters().delete(
        name=f"projects/{gcp_project}/locations/{location}/clusters/{name}"
    ).execute()

    print(delete_response)

    return delete_response
