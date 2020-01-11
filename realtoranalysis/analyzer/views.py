import secrets
from flask import render_template, request, redirect, url_for, abort, flash
from flask_login import current_user
from realtoranalysis import db
from .forms import AnalyzeForm
from realtoranalysis.models import User, Post
from realtoranalysis.scripts.property_calculations import Calculate, comma_dollar, handle_comma, remove_comma_dollar
from . import analyzer
from .functions import get_form_dict

######################################################################################################
# Analyze
######################################################################################################


@analyzer.route('/', methods=['GET', 'POST'])
def analyze():

    """
    This route is accessed from the 'Analyze' option located on the side bar navigation menu.
    The route renders a template containing a form for the user to input property details and assumptions.

    When the form is submitted:
        Values entered on the front end form are requested and assigned to variables (eg: title = request.form['title'])
        We initialize the Calculate object, and pass in these variables as parameters to make calculations
        These variables and calculations are inserted to a SQL database and linked to the user_id

        If the user is logged in:
            The user is redirected to the route /analyze/<post.id> that displays the report

        If the user is not logged in:
            The user is redirected to the route /analyze/anon/<post.id> that displays the report
    """

    form = AnalyzeForm()
    if form.is_submitted():

        # generates a string that allows the user to share private reports
        share_hex = secrets.token_hex(8)

        # Pass form inputs as variables
        form_dict = get_form_dict(request.form)
        print(form_dict)
        title = request.form['title']
        url = request.form['url']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zipcode = request.form['zipcode']

        type = request.form['type']
        year = request.form['year']
        bed = request.form['bed']
        bath = request.form['bath']
        sqft = request.form['sqft']

        price = handle_comma(request.form['price'])
        report_price = comma_dollar(handle_comma(request.form['price']))
        term = request.form['term']
        down = request.form['down']
        interest = request.form['interest']
        closing = request.form['closing']

        rent = handle_comma(request.form['rent'])
        other = handle_comma(request.form['other'])
        expenses = request.form['expenses']
        vacancy = request.form['vacancy']
        appreciation = request.form['appreciation']
        income_growth = request.form['income_growth']
        expense_growth = request.form['expense_growth']

        # calculate main metrics for property
        property = Calculate(float(price),
                             float(down),
                             float(interest),
                             float(term),
                             float(rent),
                             float(expenses),
                             float(vacancy),
                             float(closing),
                             float(other)
                             )

        cash_flow = comma_dollar(property.cashflow())
        cap_rate = property.cap_rate()
        coc = property.cashoncash()

        # check if report details are empty
        if len(title) == 0:
            title = 'Untitled'
        if len(sqft) == 0:
            sqft = '-'
        if len(bed) == 0:
            bed = '-'
        if len(bath) == 0:
            bath = '-'
        if len(year) == 0:
            year = '-'

        # when user is logged in, current_user is authenticated
        if current_user.is_authenticated:
            user = current_user
            post = Post(title=title,
                        url=url,
                        share=share_hex,
                        street=street,
                        city=city,
                        state=state,
                        zipcode=zipcode,

                        type=type,
                        year=year,
                        bed=bed,
                        bath=bath,
                        sqft=sqft,

                        price=price,
                        term=term,
                        down=down,
                        interest=interest,
                        closing=closing,

                        rent=rent,
                        other=other,
                        expenses=expenses,
                        vacancy=vacancy,
                        appreciation=appreciation,
                        income_growth=income_growth,
                        expense_growth=expense_growth,

                        report_price=report_price,
                        cash_flow=cash_flow,
                        cap_rate=cap_rate,
                        coc=coc,

                        author=user)

            db.session.add(post)
            db.session.commit()
            return redirect(url_for('analyzer.post', post_id=post.id))

        # below calls current_user.get_id() which returns 'None' when user is NOT logged in
        else:
            user = current_user.get_id()
            post = Post(title=title,
                        url=url,
                        street=street,
                        city=city,
                        state=state,
                        zipcode=zipcode,

                        type=type,
                        year=year,
                        bed=bed,
                        bath=bath,
                        sqft=sqft,

                        price=price,
                        term=term,
                        down=down,
                        interest=interest,
                        closing=closing,

                        rent=rent,
                        other=other,
                        expenses=expenses,
                        vacancy=vacancy,
                        appreciation=appreciation,
                        income_growth=income_growth,
                        expense_growth=expense_growth,

                        author=user)

            db.session.add(post)
            db.session.commit()
            return redirect(url_for('analyzer.post_anon', post_id=post.id))

    return render_template('analyze.html', form=form)


@analyzer.route('/<int:post_id>', methods=['POST', 'GET'])
def post(post_id):

    """
    The user is redirected to this route after submitting the form on the /analyze/ route
    As recap, the /analyze/ route submission inserts form inputs and calculations into a database
    The database automatically assigns a primary key "post_id" to the row data

    This route queries the database using the post id as the SQL WHERE operator (WHERE post_id = post_id)
    We now have access to the variables input on the analyze form and inserted by the /analyze/ route
    For example, we can get price by calling post.price

    We call the Calculate class defined in property_calculations.py and pass form inputs as parameters.
    We then use class methods to calculate metrics such as down payment, cap rates, etc.
    We take the results of the calculations and insert them into the dictionary {data}

    The return statement passes query results and the dictionary as a parameter in render_template()
    Now we can access the query results and calculations in the jinja2 template
    """

    post = Post.query.get_or_404(post_id)

    if post.author != current_user:
        abort(403)

    share_url = "http://www.reinvestify.com/analyze/" + str(post.id) + "/" + str(post.share)

    property = Calculate(float(post.price),
                         float(post.down),
                         float(post.interest),
                         float(post.term),
                         float(post.rent),
                         float(post.expenses),
                         float(post.vacancy),
                         float(post.closing),
                         float(post.other)
                         )

    mortgage_payment = property.mortgage_payment()
    out_of_pocket = property.outofpocket()
    vacancy_loss = property.vacancy_loss()
    operating_income = property.operating_income()
    operating_expense = property.operating_expense()
    noi = property.noi()
    cash_flow = property.cashflow()
    cap_rate = property.cap_rate()
    coc = property.cashoncash()

    # 30 year appreciation, equity, loan
    model_year, model_appreciation, model_loan, model_equity = property.year30model(float(post.appreciation))

    # 30 year cash flow
    bar_year, bar_rent = property.cash_flow_30_year(post.income_growth, post.expense_growth)

    # cash flow table
    cashflow_data = property.income_statement()

    data = {'model_year': model_year,
            'model_appreciation': model_appreciation,
            'model_loan': model_loan,
            'model_equity': model_equity,
            'bar_year': bar_year,
            'bar_rent': bar_rent,
            'price': comma_dollar(float(post.price)),
            'mortgage': comma_dollar(mortgage_payment),
            'outofpocket': comma_dollar(out_of_pocket),
            'cap_rate': cap_rate,
            'coc': coc,
            'operating_income': comma_dollar(operating_income),
            'operating_expense': comma_dollar(operating_expense),
            'cash_flow': comma_dollar(cash_flow),
            'noi': comma_dollar(noi),
            'vacancy': vacancy_loss,
            'pie_ma': (int(mortgage_payment) * 12),
            'pie_oe': remove_comma_dollar(cashflow_data['annual_operating_expenses']),
            'pie_cf': remove_comma_dollar(cashflow_data['annual_cashflow']),
            'share_url': share_url
            }

    return render_template('analyze_output.html',
                           title=post.title,
                           post=post,
                           cashflow_data=cashflow_data,
                           data=data
                           )



@analyzer.route('/anon/<int:post_id>')
def post_anon(post_id):

    """
    This route generates a property report for a user that is not registered and logged in.
    The route does the same steps as /analyze/<int:post_id>
    but does not check that current_user equals user that created the report.
    """
    post = Post.query.get_or_404(post_id)

    property = Calculate(float(post.price),
                         float(post.down),
                         float(post.interest),
                         float(post.term),
                         float(post.rent),
                         float(post.expenses),
                         float(post.vacancy),
                         float(post.closing),
                         float(post.other)
                         )

    mortgage_payment = property.mortgage_payment()
    out_of_pocket = property.outofpocket()
    vacancy_loss = property.vacancy_loss()
    operating_income = property.operating_income()
    operating_expense = property.operating_expense()
    noi = property.noi()
    cash_flow = property.cashflow()
    cap_rate = property.cap_rate()
    coc = property.cashoncash()

    # 30 year model
    model_year, model_appreciation, model_loan, model_equity = property.year30model(float(post.appreciation))

    # 30 year cash flow
    bar_year, bar_rent = property.cash_flow_30_year(post.income_growth, post.expense_growth)

    # cash flow table
    cashflow_data = property.income_statement()

    data = {'model_year': model_year,
            'model_appreciation': model_appreciation,
            'model_loan': model_loan,
            'model_equity': model_equity,
            'bar_year': bar_year,
            'bar_rent': bar_rent,
            'price': comma_dollar(float(post.price)),
            'mortgage': comma_dollar(mortgage_payment),
            'outofpocket': comma_dollar(out_of_pocket),
            'cap_rate': cap_rate,
            'coc': coc,
            'operating_income': comma_dollar(operating_income),
            'operating_expense': comma_dollar(operating_expense),
            'cash_flow': comma_dollar(cash_flow),
            'noi': comma_dollar(noi),
            'vacancy': vacancy_loss,
            'pie_ma': (int(mortgage_payment) * 12),
            'pie_oe': remove_comma_dollar(cashflow_data['annual_operating_expenses']),
            'pie_cf': remove_comma_dollar(cashflow_data['annual_cashflow']),
            }

    return render_template('analyze_output.html',
                           title=post.title,
                           post=post,
                           cashflow_data=cashflow_data,
                           data=data)




######################################################################################################
# Edit | Share | Delete |
######################################################################################################


@analyzer.route('/<int:post_id>/update', methods=['GET', 'POST'])
def update_post(post_id):
    """
    This route renders the analyze_update.html template and allows a user to update the form inputs.

    This update template differs in that the form preloads query results as values
        Using a GET request:
            On load, it first queries the database for information associated with the post_id
            It sets the form inputs as the variables we query from the database

        When we POST this form,
            We insert the form inputs back into the database
            Since when we load the update page, the original information is prefilled into the form,
                Only changes we make will be change data inserted into the database
    """
    post = Post.query.get_or_404(post_id)

    # Raise Forbidden error if current user did not create the report
    if post.author != current_user:
        abort(403)

    form = AnalyzeForm()

    if form.is_submitted():
        post.title = form.title.data
        post.street = form.street.data
        post.city = form.city.data
        post.state = form.state.data
        post.zipcode = form.zipcode.data

        post.type = form.type.data
        post.year = form.year.data
        post.bed = form.bed.data
        post.bath = form.bath.data
        post.sqft = form.sqft.data

        post.price = handle_comma(form.price.data)
        post.term = form.term.data
        post.down = form.down.data
        post.interest = form.interest.data
        post.closing = form.closing.data

        post.rent = handle_comma(form.grossrent.data)
        post.other = handle_comma(form.other.data)
        post.expenses = form.expenses.data
        post.vacancy = form.vacancy.data
        post.appreciation = form.appreciation.data
        post.income_growth = form.income_growth.data
        post.expense_growth = form.expense_growth.data

        db.session.commit()

        flash('Your post has been updated!', 'success')
        return redirect(url_for('analyzer.post', post_id=post.id))

    # This block will pre-fill the form with database values
    elif request.method == 'GET':
        form.title.data = post.title
        form.street.data = post.street
        form.city.data = post.city
        form.state.data = post.state
        form.zipcode.data = post.zipcode

        form.type.data = post.type
        form.year.data = post.year
        form.bed.data = post.bed
        form.bath.data = post.bath
        form.sqft.data = post.sqft

        form.price.data = post.price
        form.down.data = post.down
        form.interest.data = post.interest
        form.closing.data = post.closing

        form.grossrent.data = post.rent
        form.other.data = post.other
        form.expenses.data = post.expenses
        form.vacancy.data = post.vacancy
        form.appreciation.data = post.appreciation
        form.income_growth.data = post.income_growth
        form.expense_growth.data = post.expense_growth

    return render_template('analyze_update.html', form=form)


@analyzer.route('/<int:post_id>/<share>')
def shared_post(post_id, share):
    """
    This route allows a user to share a report.
    Reports are private, with access only being granted if the current_user is authenticated.

    However, in the /analyze/ route, we generated a string of random characters and inserted it into the database.

    This route will first query the data using <int:post_id>.
    Then it will check the <share> string in the uRL against the share string in the database

    IF the share string in the url is equal to the share string in the database, the report will be generated
    """
    post = Post.query.get_or_404(post_id)
    share_id = post.share

    if share == share_id:

        property = Calculate(float(post.price),
                             float(post.down),
                             float(post.interest),
                             float(post.term),
                             float(post.rent),
                             float(post.expenses),
                             float(post.vacancy),
                             float(post.closing),
                             float(post.other)
                             )

        mortgage_payment = property.mortgage_payment()
        out_of_pocket = property.outofpocket()
        vacancy_loss = property.vacancy_loss()
        operating_income = property.operating_income()
        operating_expense = property.operating_expense()
        noi = property.noi()
        cash_flow = property.cashflow()
        cap_rate = property.cap_rate()
        coc = property.cashoncash()

        # 30 year appreciation, equity, loan
        model_year, model_appreciation, model_loan, model_equity = property.year30model(float(post.appreciation))

        # 30 year cash flow
        bar_year, bar_rent = property.cash_flow_30_year(post.income_growth, post.expense_growth)

        # cash flow table
        cashflow_data = property.income_statement()

        data = {'model_year': model_year,
                'model_appreciation': model_appreciation,
                'model_loan': model_loan,
                'model_equity': model_equity,
                'bar_year': bar_year,
                'bar_rent': bar_rent,
                'price': comma_dollar(float(post.price)),
                'mortgage': comma_dollar(mortgage_payment),
                'outofpocket': comma_dollar(out_of_pocket),
                'cap_rate': cap_rate,
                'coc': coc,
                'operating_income': comma_dollar(operating_income),
                'operating_expense': comma_dollar(operating_expense),
                'cash_flow': comma_dollar(cash_flow),
                'noi': comma_dollar(noi),
                'vacancy': vacancy_loss,
                'pie_ma': (int(mortgage_payment) * 12),
                'pie_oe': remove_comma_dollar(cashflow_data['annual_operating_expenses']),
                'pie_cf': remove_comma_dollar(cashflow_data['annual_cashflow']),
                }

        return render_template('analyze_output.html',
                               title=post.title,
                               post=post,
                               cashflow_data=cashflow_data,
                               data=data
                               )
    else:
        return redirect(url_for('analyzer.analyze'))


@analyzer.route('/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):

    post = Post.query.get_or_404(post_id)

    if post.author != current_user:
        if post.author is None:
            db.session.delete(post)
            db.session.commit()
            flash('Your post has been deleted!', 'success')
            return redirect(url_for('analyze'))
        else:
            abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')

    return redirect(url_for('properties'))
