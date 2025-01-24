from flask import Flask, send_from_directory, jsonify, request
from flask import render_template
from flask_cors import CORS
import os
import openai
import re
import json
from dotenv import load_dotenv
from docx import Document

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise EnvironmentError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

openai.api_key = openai_api_key

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
    extracted_fields = data.get('extracted_fields', {})  # JSON 필드 데이터 받기

    if selection not in contract_types:
        return jsonify({"error": "잘못된 선택입니다. 1, 2, 3 중에서 선택해 주세요."})

    contract_type = contract_types[selection]

    # 1단계: 기본 계약서 템플릿 생성
    template_prompt = f"'{contract_type}'의 표준 계약서를 작성해 주세요."

    try:
        template_response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": template_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        contract_template = template_response.choices[0].message.content.strip()

        # 2단계: JSON 데이터를 이용해 계약서 업데이트
        if extracted_fields:
            update_prompt = f"""
            다음 계약서 템플릿에 주어진 JSON 데이터의 값들을 적절한 위치에 삽입해주세요.

            계약서 템플릿:
            {contract_template}

            JSON 데이터:
            {json.dumps(extracted_fields, ensure_ascii=False)}

            요구사항:
            1. JSON 데이터의 각 필드를 계약서의 적절한 위치에 삽입해주세요
            2. 데이터가 없는 필드는 '[필드명]' 형식으로 남겨두세요
            3. 계약서의 전체적인 형식과 구조는 유지해주세요
            4. 계약서 내용만 반환해주세요
            """

            update_response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": update_prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            updated_contract = update_response.choices[0].message.content.strip()
            return jsonify({"contract": updated_contract})

        return jsonify({"contract": contract_template})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/update-contract', methods=['POST'])
def update_contract():
    data = request.get_json()
    current_contract = data.get('current_contract', '')
    extracted_fields = data.get('extracted_fields', {})

    if not current_contract or not extracted_fields:
        return jsonify({"error": "계약서 내용과 필드 데이터가 필요합니다."})

    try:
        # GPT를 사용해 계약서 업데이트
        update_prompt = f"""
        다음 계약서의 내용을 주어진 JSON 데이터를 이용해 업데이트해주세요.

        현재 계약서:
        {current_contract}

        JSON 데이터:
        {json.dumps(extracted_fields, ensure_ascii=False)}

        요구사항:
        1. JSON 데이터의 각 필드를 계약서의 적절한 위치에 삽입해주세요
        2. 데이터가 없는 필드는 '[필드명]' 형식으로 남겨두세요
        3. 계약서의 전체적인 형식과 구조는 유지해주세요
        4. 계약서 내용만 반환해주세요
        """

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": update_prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        updated_contract = response.choices[0].message.content.strip()

        # Word 파일 생성
        doc = Document()
        doc.add_paragraph(updated_contract)
        file_path = './completed_contracts/completed_contract.docx'
        doc.save(file_path)

        return jsonify({"contract": updated_contract, "file_path": file_path})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/input-fields', methods=['POST'])
def get_input_fields():
    data = request.get_json()
    selection = data.get('selection')

    if selection not in contract_types:
        return jsonify({"error": "잘못된 선택입니다. 1, 2, 3 중에서 선택해 주세요."})

    contract_type = contract_types[selection]
    prompt = (
        f"'{contract_type}'의 내용을 기반으로 사용자 입력이 필요한 중요한 항목 5~10개를 선별해 주세요. "
        "만약 두 명이 상호간에 작성하는 계약서라면, '갑'의 입장에서 입력이 필요한 내용들로 선별해 주세요. 예시는 필요하지 않습니다."
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        fields_text = response.choices[0].message.content.strip()
        fields = fields_text.split('\n')

        request_message = (
            f"'{contract_type}'을/를 작성하기 위해, 다음 항목들이 잘 포함되도록 내용을 입력해 주세요! 문장 형태로 자유롭게 입력할 수 있습니다.\n\n"
        )
        for field in fields:
            request_message += f"- {field}\n"

        return jsonify({"message": request_message})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/extract-fields', methods=['POST'])
def extract_fields():
    print("[DEBUG] /extract-fields 엔드포인트 호출됨")  # 엔드포인트 호출 확인

    data = request.get_json()
    user_input = data.get('user_input')
    print(f"[DEBUG] 사용자 입력: {user_input}")  # 사용자 입력 확인

    prompt = (
        "다음 문장에서 계약서에 포함되어야 할 항목을 JSON 형태로 반환해 주세요. "
        "설명 없이 JSON 데이터만 출력해 주세요.\n"
        f"문장: {user_input}"
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        extracted_data = response.choices[0].message.content.strip()
        print(f"[DEBUG] GPT 응답 데이터: {extracted_data}")  # GPT 응답 확인

        json_match = re.search(r'\{.*\}', extracted_data, re.DOTALL)
        if json_match:
            clean_json = json_match.group()
            json_data = json.loads(clean_json)
            print(f"[DEBUG] 추출된 JSON: {json.dumps(json_data, ensure_ascii=False, indent=4)}")

            # JSON 파일 저장
            with open('./extracted_fields.json', 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=4)
            print("[INFO] JSON 파일 생성 완료: extracted_fields.json")

            return jsonify({"extracted_fields": clean_json})
        else:
            print("[ERROR] JSON 추출 실패")
            return jsonify({"error": "JSON 데이터를 추출하지 못했습니다."})

    except Exception as e:
        print(f"[ERROR] GPT API 호출 에러: {e}")
        return jsonify({"error": str(e)})

@app.route('/download', methods=['GET'])
def download_contract():
    # 저장된 Word 파일 다운로드
    file_path = './completed_contracts/completed_contract.docx'
    if os.path.exists(file_path):
        return send_from_directory('completed_contracts', 'completed_contract.docx', as_attachment=True)
    else:
        return jsonify({"error": "다운로드할 파일이 없습니다."})


if __name__ == "__main__":
    app.run(debug=True)
