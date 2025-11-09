import json
import boto3
import logging
from urllib.parse import unquote  # 导入URL解码工具

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
grades_table = dynamodb.Table('Grades')

def lambda_handler(event, context):
    try:
        logger.info(f"删除请求完整事件：{json.dumps(event)}")
        
        query_params = event.get('queryStringParameters', {})
        student_id = query_params.get('studentId')
        grade_id_encoded = query_params.get('gradeId')  # 接收编码后的gradeId
        
        # 关键修复：使用unquote完整解码（处理中文和特殊字符）
        grade_id = None
        if grade_id_encoded:
            grade_id = unquote(grade_id_encoded)  # 自动解码所有URL编码字符（包括中文、+号等）
            logger.info(f"完整解码后的gradeId：{grade_id}")  # 打印解码结果
        
        logger.info(f"接收删除参数：studentId={student_id}, 解码后gradeId={grade_id}")
        
        if not student_id or not grade_id:
            logger.error("缺少参数：studentId或gradeId")
            return {
                'statusCode': 400,
                'body': json.dumps({'message': '缺少参数：studentId或gradeId'})
            }
        
        # 执行删除
        response = grades_table.delete_item(
            Key={
                'studentId': student_id,
                'gradeId': grade_id  # 使用解码后的gradeId匹配表中数据
            },
            ReturnValues='ALL_OLD'
        )
        
        logger.info(f"删除操作响应：{json.dumps(response)}")
        if 'Attributes' in response:
            logger.info(f"成功删除数据：{json.dumps(response['Attributes'])}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': '删除成功', 'deletedItem': response['Attributes']})
            }
        else:
            logger.warning(f"未找到数据：studentId={student_id}, gradeId={grade_id}")
            return {
                'statusCode': 404,
                'body': json.dumps({'message': '未找到该成绩（主键不匹配）'})
            }
            
    except Exception as e:
        logger.error(f"删除失败：{str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'message': str(e)})
        }