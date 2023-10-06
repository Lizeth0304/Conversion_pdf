import os
import tempfile
import PyPDF2
import fitz
from flask import Flask, request, render_template, send_file
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.units import inch

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Resolución deseada para las imágenes en DPI (puedes ajustarla según tus necesidades)
RESOLUCION_DPI = 300

def convertir_pdf_a_imagenes(pdf_path, temp_dir):
    imagenes = []
    try:
        pdf = PyPDF2.PdfReader(open(pdf_path, 'rb'))
        for pagina_num in range(len(pdf.pages)):  # Corrección aquí
            page = pdf.pages[pagina_num]
            width = float(page.mediabox[2])
            height = float(page.mediabox[3])
            orientation = "horizontal" if width > height else "vertical"

            pdf_document = fitz.open(pdf_path)
            pagina = pdf_document.load_page(pagina_num)
            img = pagina.get_pixmap(matrix=fitz.Matrix(RESOLUCION_DPI / 72, RESOLUCION_DPI / 72))
            img_path = os.path.join(temp_dir, f'pagina_{pagina_num}.png')
            img.save(img_path, "png")
            imagenes.append((img_path, orientation))
    except Exception as e:
        print(f"Error al procesar el PDF: {str(e)}")
    return imagenes



def crear_pdf_desde_imagenes(imagenes, pdf_salida):
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    
    # Agrega imágenes al PDF con la resolución deseada y la orientación correcta
    for imagen_path, orientation in imagenes:
        if orientation == "horizontal":
            c.setPageSize(landscape(A4))
            c.drawImage(imagen_path, 0, 0, width=A4[1], height=A4[0])
        else:
            c.setPageSize(A4)
            c.drawImage(imagen_path, 0, 0, width=A4[0], height=A4[1])
        c.showPage()
    
    c.save()
    
    packet.seek(0)
    with open(pdf_salida, "wb") as pdf:
        pdf.write(packet.read())

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return render_template('index.html', error='No se seleccionó ningún archivo PDF.')

        pdf_file = request.files['pdf_file']

        if pdf_file.filename == '':
            return render_template('index.html', error='Nombre de archivo no válido.')

        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
        pdf_file.save(pdf_path)

        temp_dir = tempfile.mkdtemp()
        try:
            imagenes = convertir_pdf_a_imagenes(pdf_path, temp_dir)
            nuevo_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nuevo_pdf.pdf')
            
            crear_pdf_desde_imagenes(imagenes, nuevo_pdf_path)

            return send_file(nuevo_pdf_path, as_attachment=True)
        finally:
            for imagen_path, _ in imagenes:
                os.remove(imagen_path)
            os.rmdir(temp_dir)

    return render_template('index.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)