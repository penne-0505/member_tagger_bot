import os
import logging

import boto3


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DBHandler:
    def __init__(self, table_name: str | None = None, region_name: str = 'ap-northeast-1'):
        region_name = os.getenv('AWS_DEFAULT_REGION', region_name)
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=region_name,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
        self.table = self.dynamodb.Table(table_name) if table_name else None

    def create_table(self, table_name: str, key_schema: list[dict[str, str]], attribute_definitions: list[dict[str, str]], provisioned_throughput: dict[str, int]):
        try:
            self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                ProvisionedThroughput=provisioned_throughput
            )
        except Exception as e:
            logging.error(f"Error creating table: {e}")

    def put(self, item: dict[str]):
        try:
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logging.error(f"Error putting item: {e}")

    def get(self, key: dict[str, str]) -> dict[str, str | int | float | list[str] | list[int] | list[float]] | None:
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item', None)
        except Exception as e:
            logging.error(f"Error getting item: {e}")
            return None

    def delete(self, key: dict[str, str]):
        try:
            self.table.delete_item(Key=key)
            return True
        except Exception as e:
            logging.error(f"Error deleting item: {e}")

    def update(self, key: dict[str, str], update_expression: str, expression_attribute_values: dict[str, str | int | float | list[str] | list[int] | list[float]]):
        try:
            self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return True
        except Exception as e:
            logging.error(f"Error updating item: {e}")

    def query(self, key_condition_expression: str, expression_attribute_values: dict[str, str | int | float | list[str] | list[int] | list[float]]) -> list[dict[str, str | int | float | list[str] | list[int] | list[float]]]:
        try:
            response = self.table.query(
                KeyConditionExpression=key_condition_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return response.get('Items', [])
        except Exception as e:
            logging.error(f"Error querying items: {e}")
            return []
    
    def scan_tables(self) -> list[str]:
        try:
            response = self.dynamodb.list_tables()
            return response.get('TableNames', [])
        except Exception as e:
            logging.error(f"Error scanning tables: {e}")
            return []

class MemberTaggerDBHandler(DBHandler):
    '''
    db architecture:
    {
        'member_id': {
            'thread_id': 'deadline'
        }
    }
    '''
    def __init__(self):
        super().__init__('member_tagger_posts')

    def tag_member(self, member_id: str, thread_id: str, deadline: str):
        item = self.get({'member_id': member_id})
        if item:
            item[thread_id] = deadline
            self.put(item)
        else:
            self.put({'member_id': member_id, thread_id: deadline})

    def untag_member(self, member_id: str, thread_id: str):
        item = self.get({'member_id': member_id})
        if item:
            item.pop(thread_id, None)
            self.put(item)
        else:
            return False

    def get_tagged_threads(self, member_id: str) -> dict[str, str] | None:
        '''
        Returns a dictionary of tagged threads and their deadlines. If the member is not tagged, returns None.
        e.g. {'thread_id': 'deadline'}
        '''
        item = self.get({'member_id': member_id})
        if item:
            result = {k: v for k, v in item.items() if k != 'member_id'}
            return result
        else:
            return {}

    def get_tagged_members(self, thread_id: str) -> dict[str, str | int | list[str] | list[int]]:
        items = self.table.scan().get('Items', [])
        member_ids = [item['member_id'] for item in items if str(thread_id) in item]
        deadline = [item[str(thread_id)] for item in items if str(thread_id) in item]
        deadline = deadline[0] if deadline else None
        result = {'ids': member_ids, 'deadline': deadline}
        return result

    def get_deadline(self, member_id: str, thread_id: str) -> str | None:
        item = self.get({'member_id': member_id})
        return item.get(str(thread_id), None)

    def get_all_tagged_threads(self) -> dict[str, dict[str, str]]:
        '''return: {member_id: {thread_id: deadline}}'''
        items = self.table.scan().get('Items', [])
        result = {}
        for item in items:
            member_id = item.pop('member_id')
            result[member_id] = {k: v for k, v in item.items()}
        return result


class MemberTaggerNotifyDBHandler(DBHandler):
    '''
    db architecture:
    {
        'guild_id': guild_id(int),
        'info': {
            member_id(int): notify(bool)
        }
    }
    '''
    def __init__(self):
        super().__init__('member_tagger_notify')
    
    def set_guild_id(self, guild_id: int):
        self.put({'guild_id': guild_id, 'info': {}})
        return True
    
    def set_notify_state(self, guild_id: int, member_id: int, notify: bool):
        member_id = str(member_id)
        item = self.get({'guild_id': guild_id})
        data = item['info'] if item else {}
        data[member_id] = notify
        self.put({'guild_id': guild_id, 'info': data})

    
    def get_notify_state(self, guild_id: int, member_id: int) -> bool | None:
        member_id = str(member_id)
        item = self.get({'guild_id': guild_id})
        return item['info'].get(member_id, None) if item else None
    
    def get_guild_notify_states(self, guild_id: int) -> dict[int, bool]:
        item = self.get({'guild_id': guild_id})
        return item['info'] if item else {}
    
    def get_guilds(self) -> list[int]:
        items = self.table.scan().get('Items', [])
        return [item['guild_id'] for item in items]

    def toggle_notify_state(self, guild_id: int, member_id: int) -> bool:
        member_id = str(member_id)
        item = self.get({'guild_id': guild_id})
        data = item['info'] if item else {}
        data[member_id] = not data.get(member_id, False)
        self.put({'guild_id': guild_id, 'info': data})
        return data[member_id]
    
    def get_members(self, guild_id: int) -> list[int]:
        '''for sync with guild members'''
        item = self.get({'guild_id': guild_id})
        return list(item['info'].keys()) if item else []


if __name__ == '__main__':
    pass
