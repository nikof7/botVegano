from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.messaging_response import MessagingResponse
import urllib3 as urllib
from PIL import Image
import requests
from io import BytesIO
import cv2
from pyzbar.pyzbar import decode

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bot.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Iniciar tabla
db = SQLAlchemy(app)

class Products(db.Model):
	""" Es vegano y es celiaco toma los valores de si o no. """
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String)
	code = db.Column(db.Integer)
	isvegan = db.Column(db.String)
	comment = db.Column(db.String)

	def __repr__(self):
		return "<Producto %r>" % self.name

def img_to_code(url):
    # Busca un producto en la base de datos, utilizando su código de barras.
    response = requests.get(url)
    try:
        img = Image.open(BytesIO(response.content))
        decoding = str(decode(img)[0][0])
        inc_code = decoding.split("'")[1]
    except:
        inc_code = False
    return inc_code

def search_code(inc_code):

	query = Products.query.filter_by(code=inc_code).first()
	
	if query:
		exists = True
		product_name = query.name
		is_vegan = query.isvegan.lower()

	if query == None:
		exists = False
		product_name = " "
		is_vegan = " "

	return exists, product_name, is_vegan

def split_txt(inc_msg_body):
	txt_msg_ = []
	str_splitted = inc_msg_body.split(",")
	for i in str_splitted:
		txt_msg_.append(' '.join(i.split()))
	return txt_msg_

def change_product(inc_code, is_vegan):
	try:
		product = Products.query.filter_by(code=inc_code).first()
		old_parameter = product.isvegan
		product.isvegan = is_vegan
		db.session.commit()
		msg.body(f'Se modificó satisfactoriamente el producto {product.name}.\nDe {old_parameter} a {is_vegan} vegano.')
		responded = True
	except:
		msg.body(f'❌ Error al modificar el producto, prueba nuevamente. ❌')
		responded = True

@app.route('/mybot', methods = ['POST', 'GET'])
def mybot():
	
	# Variables de respuesta
	msg_ERROR = "Algo salió mal."
	msg_ERROR_NEW_PRODUCT = "Para crear un nuevo producto debes escribir\nNuevo, titulo, ¿es vegano?, comment\nEjemplo: Nuevo, Pure de papas Hornex, si, alto en sodio."
	msg_ERROR_READ_IMG = "No se pudo leer la imagen."
	msg_ERROR_MODIFY = "Para modificar un producto, debes enivar una foto del código y escribir\nModificar, si/no"

	# Variables para manejar los mensajes.
	resp = MessagingResponse()
	msg = resp.message()
	received = request.values
	responded = False

	# Roles
	admins = ("59898969206","59892964971")

	inc_phone_number = received.get('WaId')

	# Este if es para que no entre a este código cuando llega el mensaje de 'received' y 'delivered'
	if received.get('SmsStatus') == 'received':	
			
		inc_msg_body = received.get('Body')
		inc_msg_media = received.get('MediaUrl0')
		usr_name = received.get('ProfileName')
		txt_msg = split_txt(inc_msg_body)

		# Texto e imagen para admins
		if inc_msg_body and not inc_msg_media == None and inc_phone_number in admins and not responded:

			# Si el texto empieza con NUEVO, es para agregar un producto.
			if txt_msg[0].lower() == 'nuevo' and len(txt_msg) >=3 and inc_phone_number in admins and not responded:
				
				inc_code = img_to_code(inc_msg_media)

				# Se pudo leer la imagen:
				if inc_code != False and not responded: 
					
					product_info = search_code(inc_code)
					
					# Respuesta a cuando el código se encuentra en la base de datos.
					if product_info[0] ==  True:
						if product_info[2] == "si":
							msg.body(f'¡No se pudo crear el nuevo producto, {product_info[1]} ya se encuentra registrado y es vegano!')
							responded = True
						if product_info[2] == "no":
							msg.body(f'¡No se pudo crear el nuevo producto, {product_info[1]} ya se encuentra registrado y NO es vegano!')
							responded = True
						elif not responded:
							msg.body(msg_ERROR_NEW_PRODUCT)
							responded = True
						
					if product_info[0] == False and txt_msg and not responded:
					
						name = txt_msg[1]
						isvegan = txt_msg[2]
						code = int(inc_code)

						# Este if es porque los comentarios no son obligatorios.
						if len(txt_msg) > 3:
							comment = txt_msg[3]
						else:
							comment = " - "

						nuevo_producto = Products(name = name, code=code, isvegan = isvegan, comment=comment)

						# Añade el nuevo producto a la base de datos.
						try:
							db.session.add(nuevo_producto)
							db.session.commit()
							msg.body(f'Se agregó el producto {name}')
							responded = True
						except:
							msg.body(f'❌ Error al ingresar nuevo producto, prueba nuevamente. ❌')
							responded = True

				# No se pudo leer la imagen.
				if inc_code == False:
					msg.body(msg_ERROR_READ_IMG)
					responded = True

			if txt_msg[0].lower() == 'modificar' and len(txt_msg) == 2 and inc_phone_number in admins and not responded:
				inc_code = img_to_code(inc_msg_media)

				if inc_code != False and not responded: 
					
					product_info = search_code(inc_code)
					
					# Respuesta a cuando el código se encuentra en la base de datos.
					if product_info[0] ==  True and not responded:
						if txt_msg[1] == "si" or txt_msg[1] == "no":
							isvegan = txt_msg[1]
							code = int(inc_code)
							try:
								product = Products.query.filter_by(code=inc_code).first()
								old_parameter = product.isvegan
								product.isvegan = isvegan
								db.session.commit()
								msg.body(f'Se modificó satisfactoriamente el producto {product.name}.\nDe {old_parameter} a {isvegan} vegano.')
								responded = True
							except:
								msg.body(f'❌ Error al modificar el producto, prueba nuevamente. ❌')
								responded = True
						elif not responded:
							msg.body(msg_ERROR_MODIFY)
							responded = True

					# Cuando no se encuentra en la base de datos
					if product_info[0] == False and txt_msg and not responded:
						msg.body(f'El producto ingresado no se encuentra en la base de datos')
						responded = True

				# No se pudo leer la imagen.
				if inc_code == False:
					msg.body(msg_ERROR_READ_IMG)
					responded = True

			# Respuesta cuando el texto está mal.
			if txt_msg[0].lower() == 'nuevo' and not responded:
				msg.body(msg_ERROR_NEW_PRODUCT)
				responded = True

			if txt_msg[0].lower() == 'modificar' and not responded:
				msg.body(msg_ERROR_MODIFY)
				responded = True

			if not responded:
				msg.body(msg_ERROR)
				responded = True

		# Llega imágen, leo el código y devuelvo si está en la base o no (ignoro texto).
		if not inc_msg_media == None and not responded:
			
			# Leo el code de barras de la imagen
			inc_code = img_to_code(inc_msg_media)

			# Error al leer la imagen.
			if inc_code == False and not responded:
				msg.body(msg_ERROR_READ_IMG)
				responded = True

			if inc_code != False and not responded:
				product_info = search_code(inc_code)
				if product_info[0] ==  True:
					if product_info[2] == "si":
						msg.body(f'¡El producto: {product_info[1]} es vegano!')
						responded = True

					if product_info[2] == "no":
						msg.body(f'¡El producto: {product_info[1]} NO es vegano!')
						responded = True

				if product_info[0] == False:
					msg.body('El producto no se encuentra en nuestra base de datos. Si quieres ayudarnos escribe _*"Ayuda"*_')
					responded = True 

			# Por las dudas de que exista algún error.
			if not responded:
				msg.body(msg_ERROR)
				responded = True

		# Solo texto (AYUDA)
		if txt_msg[0].lower() == "ayuda" and not responded:
			msg.body('🌱 Para ayudarte a conocer si un producto es vegano, solo mándanos una foto del _*código de barras*_.\n\n🆘 ¿Quieres ayudar a generar nuestra base de datos?, infórmanos sobre algún producto vegano en este formulario:\nhttps://forms.gle/P7pg5FJSt6dZYFrT9\n\n💰 Si quieres *colaborar* con este emprendimiento, puedes ayudarnos a través de *mercadopago*\nhttps://mpago.la/1G1a9GF')
			responded = True

		# Solo texto
		if not inc_msg_media and not responded:
			msg.body(f'🌱🤖 *{usr_name}*, soy un ```robot vegano``` que te ayuda a conocer qué Products son *aptos*.\n\n📷 Si me envías una foto del *código de barras* del producto, puedo decirte si es vegano o no. Pueden ser alimentos, artículos de higiene personal, cosméticos, etc.\n\nℹ️ Para más información escribe _*"Ayuda"*_.\n\n🌸 Gracias por usar _*botVegano_uy*_')
			responded = True

		if not responded:
			msg.body(msg_ERROR)
			responded = True

	return str(resp)

if __name__ == "__main__":
	app.run()