import boto3
import json

# 连接DynamoDB的StudentInfo表（表名必须与你创建的一致）
dynamodb = boto3.resource('dynamodb')
student_table = dynamodb.Table('StudentInfo')  # 表名：StudentInfo

def lambda_handler(event, context):
    try:
        # 从Cognito授权信息中获取学生学号（username即studentId，需与StudentInfo表的主键一致）
        # 注意：确保Cognito学生用户的username与StudentInfo表中的studentId完全匹配
        student_id = event['requestContext']['authorizer']['claims']['cognito:username']
        
        # 从StudentInfo表中查询该学生的信息
        response = student_table.get_item(
            Key={
                'studentId': student_id  # 主键查询，studentId为表的分区键
            }
        )
        
        # 提取查询结果（若不存在，Item字段会缺失）
        student_info = response.get('Item')
        
        # 处理“学生信息不存在”的情况
        if not student_info:
            return {
                'statusCode': 404,  # 未找到
                'headers': {
                    # CORS头：必须与前端域名完全一致（无斜杠）
                    'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'message': f'未找到学号为{student_id}的学生信息'})
            }
        
        # 正常返回学生信息（只包含需要前端展示的字段）
        return {
            'statusCode': 200,  # 成功
            'headers': {
                'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'studentId': student_info.get('studentId'),  # 学号（必返）
                'name': student_info.get('name', '未填写'),  # 姓名（默认“未填写”）
                'className': student_info.get('className', '未填写'),  # 班级
                'gender': student_info.get('gender', '未填写'),  # 性别
                # 如需其他字段（如生日、专业），可在此处添加
            })
        }
    
    # 捕获所有异常（如权限不足、表不存在、数据格式错误等）
    except Exception as e:
        print(f"查询学生信息时出错：{str(e)}")  # 打印错误到CloudWatch日志
        return {
            'statusCode': 500,  # 服务器错误
            'headers': {
                'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': '查询个人信息失败，请稍后重试'})
        }
