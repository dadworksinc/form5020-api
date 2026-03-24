from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import requests
import io
import os

app = Flask(__name__)
CORS(app)

PDF_URL = 'https://raw.githubusercontent.com/dadworksinc/risk-assets/main/form5020.pdf'

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/fill-form5020', methods=['POST', 'OPTIONS'])
def fill_form5020():
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()

        # Fetch the official PDF
        pdf_response = requests.get(PDF_URL, timeout=10)
        pdf_response.raise_for_status()

        reader = PdfReader(io.BytesIO(pdf_response.content))
        writer = PdfWriter()
        writer.append(reader)

        # Build field map from incoming data
        fields = {
            '1_FIRM_NAME':                    data.get('firm_name', ''),
            'Ia_Policy_Number':               data.get('policy_number', ''),
            '2_MAILING_ADDRESS_Number':       data.get('mailing_address', ''),
            '2a_Phone_Number':                data.get('phone_number', ''),
            '4_NATURE_OF_BUSINESS_eg_P':      data.get('industry', ''),
            '7_DATE_OF_INJURY__ONSET_O':      data.get('injury_date', ''),
            '8_AM2':                          data.get('injury_time', ''),
            'AM1':                            data.get('shift_start_time', ''),
            '17_DATE_OF_EMPLOYERS_KNOW':      data.get('knowledge_date', ''),
            '18_DATE_EMPLOYEE_PROVIDED':      data.get('dwc1_date', ''),
            '19_SPECIFIC_INJURYILLNESS':      data.get('injury_description', ''),
            '20_LOCATION_WHERE_EVENT_O':      data.get('location', ''),
            '20a_COUNTY':                     data.get('county', 'Riverside'),
            '22_DEPARTMENT_WHERE_EVENT':      data.get('department', ''),
            '24_EQUIPMENT_MATERIALS_AN':      data.get('equipment', ''),
            '25_SPECIFIC_ACTIVITY_THE':       data.get('activity', ''),
            '26_HOW_INJURY_ILLNESS':          data.get('description', ''),
            '27_name _address_of_physician':  data.get('physician', ''),
            '29_HOSP_TA_ZED_AS_AN_NAl':      data.get('hospital_name', ''),
            '30_EMPLO_CC_NAME':               data.get('employee_name', ''),
            '33_HOME_ADDRESS_IN_be_Sto':      data.get('employee_address', ''),
            '33a_PHONE_NUMBER':               data.get('employee_phone', ''),
            '35_OCC_UPAT_ON_Ppqj_a_on':      data.get('occupation', ''),
            '36_DATE_OF_H_RE_mmiddlyy':       data.get('hire_date', ''),
            'Completed_By_type_or_prin':      data.get('completed_by', ''),
        }

        # Radio/checkbox fields
        radio_fields = {}

        # Type of employer - Private
        radio_fields['Group2'] = '/Private'

        # On premises - Yes
        radio_fields['Group6'] = '/Yes'

        # Lost time
        radio_fields['Group3'] = '/Yes' if data.get('lost_time') else '/No'

        # Hospitalized
        radio_fields['Group8'] = '/Yes' if data.get('hospitalized') else '/No'

        # ER treated
        radio_fields['Group9'] = '/Yes' if data.get('er_treated') else '/No'

        # Other workers injured
        radio_fields['Group7'] = '/Yes' if data.get('other_injured') else '/No'

        # Sex
        radio_fields['Group11'] = '/Male' if data.get('is_male', True) else '/Female'

        # Employment status
        radio_fields['Group100'] = '/regular, full-time'

        # Other payments
        radio_fields['Group101'] = '/No'

        # Write text fields
        writer.update_page_form_field_values(
            writer.pages[0],
            fields,
            auto_regenerate=False
        )

        # Write radio fields
        for field_name, value in radio_fields.items():
            try:
                writer.update_page_form_field_values(
                    writer.pages[0],
                    {field_name: value},
                    auto_regenerate=False
                )
            except Exception:
                pass

        # Save to buffer
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        emp_name = data.get('employee_name', 'Unknown').replace(' ', '_')
        inj_date = data.get('injury_date', '').replace('/', '-')
        filename = f"Form5020_{emp_name}_{inj_date}.pdf"

        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
