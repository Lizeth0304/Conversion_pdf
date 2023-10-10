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
import cv2
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  
CORS(app, resources={r"/procesar-pdf": {"origins": "*"}})

app.config['UPLOAD_FOLDER'] = 'uploads'

# Resolución deseada para las imágenes en DPI (puedes ajustarla según tus necesidades)
RESOLUCION_DPI = 300

def detectar_orientacion(imagen_path):
    # Cargar la imagen
    imagen = cv2.imread(imagen_path)

    # Obtener el ancho y el alto de la imagen
    ancho, alto = imagen.shape[1], imagen.shape[0]

    # Determinar la relación entre ancho y alto
    relacion_ancho_alto = ancho / alto

    # Establecer un umbral para determinar la orientación
    umbral_orientacion = 1.0  # Puedes ajustar este valor según tus necesidades

    if relacion_ancho_alto > umbral_orientacion:
        # La imagen es más ancha que alta, no es necesario rotar
        orientacion = "horizontal"
    else:
        # La imagen es más alta que ancha, necesita rotación
        orientacion = "vertical"

    return orientacion

def convertir_pdf_a_imagenes(pdf_path, temp_dir):
    imagenes = []
    try:
        pdf = PyPDF2.PdfReader(open(pdf_path, 'rb'))
        for pagina_num in range(len(pdf.pages)):  # Corrección aquí
            page = pdf.pages[pagina_num]
            width = float(page.mediabox[2])
            height = float(page.mediabox[3])

            pdf_document = fitz.open(pdf_path)
            pagina = pdf_document.load_page(pagina_num)
            img = pagina.get_pixmap(matrix=fitz.Matrix(RESOLUCION_DPI / 72, RESOLUCION_DPI / 72))
            img_path = os.path.join(temp_dir, f'pagina_{pagina_num}.png')      
            img.save(img_path, "png")
            orientation = detectar_orientacion(img_path)
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

@app.route('/procesar-pdf', methods=['POST'])
def procesar_pdf():
    if 'pdf_file' not in request.files:
        return "No se seleccionó ningún archivo PDF.", 400

    pdf_file = request.files['pdf_file']

    if pdf_file.filename == '':
        return "Nombre de archivo no válido.", 400

    try:
        # Guarda el archivo PDF en una ubicación temporal
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
        pdf_file.save(pdf_path)

        temp_dir = tempfile.mkdtemp()
        try:
            imagenes = convertir_pdf_a_imagenes(pdf_path, temp_dir)
            nombre_original = os.path.splitext(pdf_file.filename)[0]  # Obtener el nombre original sin extensión
            nuevo_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{nombre_original}-Formateado.pdf')

            crear_pdf_desde_imagenes(imagenes, nuevo_pdf_path)

            # Devuelve el nuevo PDF como respuesta
            return send_file(nuevo_pdf_path, as_attachment=True)

        finally:
            for imagen_path, _ in imagenes:
                os.remove(imagen_path)
            os.rmdir(temp_dir)

    except Exception as e:
        return f"Error al procesar el PDF: {str(e)}", 500

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
