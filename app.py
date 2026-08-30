from flask import Flask, request, render_template, redirect, url_for, flash, session
from db_connection import obtener_conexion
from mysql.connector import Error
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'mcosia_s12'

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('nombre_usuario')
        contrasena = request.form.get('contraseña')

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor(dictionary=True)
                query = "SELECT * FROM Usuario WHERE correo = %s"
                cursor.execute(query, (correo,))
                usuario = cursor.fetchone()
                cursor.close()
                conexion.close()

                if usuario and (check_password_hash(usuario['contrasena'], contrasena) or usuario['contrasena'] == contrasena):
                    session['usuario'] = f"{usuario['nombre']} {usuario['apellido']}"
                    session['correo'] = usuario['correo']
                    session['id_usuario'] = usuario['id_usuario']
                    session['es_cliente'] = usuario.get('es_cliente', True)
                    flash(f"Bienvenido/a, {usuario['nombre']}!", 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Correo o contraseña incorrectos', 'danger')
            except Error as e:
                flash(f'Error al consultar la base de datos: {e}', 'danger')
        else:
            flash('No se pudo conectar a la base de datos', 'danger')

    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')
        direccion_envio = request.form.get('direccion_envio')

        if not nombre or not apellido or not correo or not contrasena or not direccion_envio:
            flash('Por favor completa todos los campos requeridos', 'danger')
            return render_template('registro.html')

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor(dictionary=True)

                cursor.execute("SELECT COALESCE(MAX(id_usuario), 0) + 1 AS next_id FROM Usuario")
                res = cursor.fetchone()
                next_id = res['next_id'] if isinstance(res, dict) else res[0]
                contrasena_encriptada = generate_password_hash(contrasena)

                query = """
                    INSERT INTO Usuario (id_usuario, nombre, apellido, correo, contrasena, es_cliente, direccion_envio)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (next_id, nombre, apellido, correo, contrasena_encriptada, True, direccion_envio or None))
                conexion.commit()
                cursor.close()
                conexion.close()

                flash('Cuenta creada exitosamente. Ya puedes iniciar sesión.', 'success')
                return redirect(url_for('login'))

            except Error as e:
                if e.errno == 1062:
                    flash('El correo ya se encuentra registrado.', 'danger')
                else:
                    flash(f'Error al registrar la cuenta: {e}', 'danger')
            finally:
                if conexion.is_connected():
                    conexion.close()
        else:
            flash('No se pudo establecer conexión con la base de datos.', 'danger')

    return render_template('registro.html')

@app.route('/index')
def index():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder', 'danger')
        return redirect(url_for('login'))

    libros = []
    pedidos = []
    conexion = obtener_conexion()
    if conexion:
        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Libro ORDER BY titulo ASC")
            libros = cursor.fetchall()

            if session.get('es_cliente') and session.get('id_usuario'):
                query_pedidos = """
                    SELECT p.id_pedido, l.titulo, l.precio, p.cantidad, 
                           (p.cantidad * l.precio) AS total, p.fecha_pedido
                    FROM Pedido p
                    JOIN Libro l ON p.id_libro = l.id_libro
                    WHERE p.id_usuario = %s
                    ORDER BY p.fecha_pedido DESC, p.id_pedido DESC
                """
                cursor.execute(query_pedidos, (session['id_usuario'],))
                pedidos = cursor.fetchall()
            elif not session.get('es_cliente'):
                query_pedidos_admin = """
                    SELECT p.id_pedido, u.nombre, u.apellido, u.correo, u.direccion_envio,
                           l.titulo, l.precio, p.cantidad, 
                           (p.cantidad * l.precio) AS total, p.fecha_pedido
                    FROM Pedido p
                    JOIN Usuario u ON p.id_usuario = u.id_usuario
                    JOIN Libro l ON p.id_libro = l.id_libro
                    ORDER BY p.fecha_pedido DESC, p.id_pedido DESC
                """
                cursor.execute(query_pedidos_admin)
                pedidos = cursor.fetchall()

            cursor.close()
        except Error as e:
            flash(f'Error al obtener los datos: {e}', 'danger')
        finally:
            if conexion.is_connected():
                conexion.close()
    else:
        flash('No se pudo conectar a la base de datos.', 'danger')

    return render_template('index.html', libros=libros, pedidos=pedidos)

@app.route('/crear_libro', methods=['POST'])
def crear_libro():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder', 'danger')
        return redirect(url_for('login'))

    if session.get('es_cliente', True):
        flash('Acceso denegado: solo los administradores pueden registrar libros', 'danger')
        return redirect(url_for('index'))

    titulo = request.form.get('titulo', '').strip()
    autor = request.form.get('autor', '').strip()
    precio_str = request.form.get('precio', '').strip()
    stock_str = request.form.get('stock', '').strip()

    if not titulo or not autor or not precio_str or not stock_str:
        flash('Todos los campos del libro son obligatorios', 'danger')
        return redirect(url_for('index'))

    try:
        precio = float(precio_str)
        stock = int(stock_str)
        if precio <= 0:
            flash('El precio debe ser un número mayor a 0', 'danger')
            return redirect(url_for('index'))
        if stock < 0:
            flash('El stock no puede ser negativo', 'danger')
            return redirect(url_for('index'))
    except ValueError:
        flash('Precio o stock con formato numérico inválido', 'danger')
        return redirect(url_for('index'))

    conexion = obtener_conexion()
    if conexion:
        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute("SELECT COALESCE(MAX(id_libro), 0) + 1 AS next_id FROM Libro")
            res = cursor.fetchone()
            next_id = res['next_id'] if isinstance(res, dict) else res[0]

            query = """
                INSERT INTO Libro (id_libro, titulo, autor, precio, stock)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (next_id, titulo, autor, precio, stock))
            conexion.commit()
            cursor.close()
            flash(f'¡Libro "{titulo}" agregado exitosamente!', 'success')
        except Error as e:
            flash(f'Error al guardar el libro: {e}', 'danger')
        finally:
            if conexion.is_connected():
                conexion.close()
    else:
        flash('No se pudo conectar a la base de datos', 'danger')

    return redirect(url_for('index'))

@app.route('/comprar_libro', methods=['POST'])
def comprar_libro():
    if 'usuario' not in session or 'id_usuario' not in session:
        flash('Debes iniciar sesión para realizar compras', 'danger')
        return redirect(url_for('login'))

    if not session.get('es_cliente', True):
        flash('Los administradores no pueden realizar compras de clientes', 'danger')
        return redirect(url_for('index'))

    id_usuario = session.get('id_usuario')
    id_libro_str = request.form.get('id_libro')
    cantidad_str = request.form.get('cantidad', '1')

    if not id_libro_str or not cantidad_str:
        flash('Datos de compra incompletos', 'danger')
        return redirect(url_for('index'))

    try:
        id_libro = int(id_libro_str)
        cantidad = int(cantidad_str)
        if cantidad <= 0:
            flash('La cantidad debe ser mayor a 0', 'danger')
            return redirect(url_for('index'))
    except ValueError:
        flash('Cantidad o código de libro inválido', 'danger')
        return redirect(url_for('index'))

    conexion = obtener_conexion()
    if conexion:
        try:
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("SELECT id_libro, titulo, stock, precio FROM Libro WHERE id_libro = %s", (id_libro,))
            libro = cursor.fetchone()

            if not libro:
                flash('El libro seleccionado no existe', 'danger')
                return redirect(url_for('index'))

            if libro['stock'] < cantidad:
                flash(f'Stock insuficiente para "{libro["titulo"]}". Solo quedan {libro["stock"]} disponibles.', 'danger')
                return redirect(url_for('index'))

            cursor.execute("SELECT COALESCE(MAX(id_pedido), 0) + 1 AS next_id FROM Pedido")
            res = cursor.fetchone()
            next_pedido_id = res['next_id'] if isinstance(res, dict) else res[0]

            fecha_hoy = date.today()
            query_pedido = """
                INSERT INTO Pedido (id_pedido, id_usuario, id_libro, cantidad, fecha_pedido)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query_pedido, (next_pedido_id, id_usuario, id_libro, cantidad, fecha_hoy))

            query_stock = "UPDATE Libro SET stock = stock - %s WHERE id_libro = %s"
            cursor.execute(query_stock, (cantidad, id_libro))

            conexion.commit()
            cursor.close()
            flash(f'¡Compra exitosa! Has comprado {cantidad} unidad(es) de "{libro["titulo"]}".', 'success')

        except Error as e:
            conexion.rollback()
            flash(f'Error al procesar la compra: {e}', 'danger')
        finally:
            if conexion.is_connected():
                conexion.close()
    else:
        flash('No se pudo conectar a la base de datos', 'danger')

    return redirect(url_for('index'))

@app.route('/editar_libro/<int:id_libro>', methods=['GET', 'POST'])
def editar_libro(id_libro):
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder', 'danger')
        return redirect(url_for('login'))

    if session.get('es_cliente', True):
        flash('Acceso no permitido: solo los administradores pueden editar libros', 'danger')
        return redirect(url_for('index'))

    conexion = obtener_conexion()
    if not conexion:
        flash('No se pudo conectar a la base de datos', 'danger')
        return redirect(url_for('index'))

    try:
        cursor = conexion.cursor(dictionary=True)

        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            autor = request.form.get('autor', '').strip()
            precio_str = request.form.get('precio', '').strip()
            stock_str = request.form.get('stock', '').strip()

            if not titulo or not autor or not precio_str or not stock_str:
                flash('Todos los campos son obligatorios', 'danger')
                return redirect(url_for('editar_libro', id_libro=id_libro))

            try:
                precio = float(precio_str)
                stock = int(stock_str)
                if precio <= 0:
                    flash('El precio debe ser mayor a 0', 'danger')
                    return redirect(url_for('editar_libro', id_libro=id_libro))
                if stock < 0:
                    flash('El stock no puede ser negativo', 'danger')
                    return redirect(url_for('editar_libro', id_libro=id_libro))
            except ValueError:
                flash('Formato inválido en precio o stock', 'danger')
                return redirect(url_for('editar_libro', id_libro=id_libro))

            query_update = """
                UPDATE Libro
                SET titulo = %s, autor = %s, precio = %s, stock = %s
                WHERE id_libro = %s
            """
            cursor.execute(query_update, (titulo, autor, precio, stock, id_libro))
            conexion.commit()
            cursor.close()
            flash(f'Libro "{titulo}" actualizado correctamente', 'success')
            return redirect(url_for('index'))

        cursor.execute("SELECT * FROM Libro WHERE id_libro = %s", (id_libro,))
        libro = cursor.fetchone()
        cursor.close()

        if not libro:
            flash('El libro no existe', 'danger')
            return redirect(url_for('index'))

        return render_template('editar_libro.html', libro=libro)

    except Error as e:
        flash(f'Error de base de datos: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        if conexion.is_connected():
            conexion.close()

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)