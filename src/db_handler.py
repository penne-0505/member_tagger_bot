import boto3
from typing import Any, Dict, List

class DBHandler:
    def __init__(self, table_name: str | None = None):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name) if table_name else None

    def create_table(self, table_name: str, key_schema: List[Dict[str, str]], attribute_definitions: List[Dict[str, str]], provisioned_throughput: Dict[str, int]):
        try:
            self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                ProvisionedThroughput=provisioned_throughput
            )
        except Exception as e:
            print(f"Error creating table: {e}")

    def put(self, item: Dict[str, Any]):
        try:
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error putting item: {e}")

    def get(self, key: Dict[str, str]) -> Dict[str, Any] | None:
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item', None)
        except Exception as e:
            print(f"Error getting item: {e}")
            return None

    def delete(self, key: Dict[str, str]):
        try:
            self.table.delete_item(Key=key)
            return True
        except Exception as e:
            print(f"Error deleting item: {e}")

    def update(self, key: Dict[str, str], update_expression: str, expression_attribute_values: Dict[str, Any]):
        try:
            self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return True
        except Exception as e:
            print(f"Error updating item: {e}")

    def query(self, key_condition_expression: str, expression_attribute_values: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            response = self.table.query(
                KeyConditionExpression=key_condition_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error querying items: {e}")
            return []

class MemberTaggerDBHandler(DBHandler):
    def __init__(self):
        super().__init__('member_tagger_posts')

    def tag_member(self, member_id: str, post_id: str, deadline: str):
        item = self.get({'member_id': member_id})
        if item:
            item[post_id] = deadline
            self.put(item)
        else:
            self.put({'member_id': member_id, 'post_id': post_id, 'deadline': deadline})

    def untag_member(self, member_id: str, post_id: str):
        item = self.get({'member_id': member_id})
        if item:
            item.pop(post_id, None)
            self.put(item)
        else:
            return False

    def get_tagged_posts(self, member_id: str) -> Dict[str, str] | None:
        item = self.get({'member_id': member_id})
        if item:
            result = {k: v for k, v in item.items() if k != 'member_id'}
            return result
        return None

    def get_deadline(self, member_id: str, post_id: str) -> str | None:
        item = self.get({'member_id': member_id})
        return item.get(post_id, None)

    def get_all_tagged_posts(self) -> Dict[str, Dict[str, str]]:
        items = self.table.scan().get('Items', [])
        result = {}
        for item in items:
            member_id = item.pop('member_id')
            result[member_id] = {k: v for k, v in item.items()}
        return result


if __name__ == '__main__':
    pass