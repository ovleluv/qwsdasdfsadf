from flask import Flask, send_from_directory, jsonify, request, render_template
from flask_cors import CORS
import os
import openai
import re
import json
from docx import Document

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# 환경 변수에서 API 키 로드
api_key = os.environ.get("OPENAI_API_KEY")

# API 키가 설정되지 않았을 경우 에러 처리
if not api_key:
    raise ValueError("OpenAI API 키가 설정되지 않았습니다. 환경 변수를 확인하세요.")

openai.api_key = api_key

contract_types = {
    "1": "부동산임대차계약서",
    "2": "위임장",
    "3": "소장"
}

@app.route('/')
def serve():
    return render_template('index.html')

@app.route('/select', methods=['POST'])
def select():
    data = request.get_json()
    selection = data.get('selection')

    if selection in contract_types:
        response = f"선택하신 계약서는 '{contract_types[selection]}'입니다. 이어지는 계약서 예시 샘플을 확인해 주세요"
    else:
        response = "잘못된 선택입니다. 1, 2, 3 중에서 선택해 주세요."

    return jsonify({"message": response})

@app.route('/generate', methods=['POST'])
def generate_contract():
    data = request.get_json()
    selection = data.get('selection')
    extracted_fields = data.get('extracted_fields', {})

    if selection not in contract_types:
        return jsonify({"error": "잘못된 선택입니다. 1, 2, 3 중에서 선택해 주세요."})

    contract_type = contract_types[selection]

    template_prompt = f"'{contract_type}'의 표준 계약서를 작성해 주세요."

    try:
        template_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": template_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        contract_template = template_response['choices'][0]['message']['content'].strip()

        if extracted_fields:
            update_prompt = f"""
            다음 계약서 템플릿에 JSON 데이터의 값을 적절한 위치에 삽입해주세요.

            계약서 템플릿:
            {contract_template}

            JSON 데이터:
            {json.dumps(extracted_fields, ensure_ascii=False)}

            요구사항:
            1. JSON 데이터의 각 필드를 계약서의 적절한 위치에 삽입해주세요.
            2. 데이터가 없는 필드는 '[필드명]' 형식으로 남겨두세요.
            3. 계약서의 전체적인 형식과 구조는 유지해주세요.
            """

            update_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": update_prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            updated_contract = update_response['choices'][0]['message']['content'].strip()
            return jsonify({"contract": updated_contract})

        return jsonify({"contract": contract_template})

    except openai.error.OpenAIError as e:
        return jsonify({"error": f"OpenAI API 호출 실패: {str(e)}"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/download', methods=['GET'])
def download_contract():
    file_path = './completed_contracts/completed_contract.docx'
    if os.path.exists(file_path):
        return send_from_directory('completed_contracts', 'completed_contract.docx', as_attachment=True)
    else:
        return jsonify({"error": "다운로드할 파일이 없습니다."})

if __name__ == "__main__":
    app.run(debug=True)
