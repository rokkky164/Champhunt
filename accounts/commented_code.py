# class LoanView(LoginRequiredMixin, CountNewsMixin, View):

#     def get(self, request, *args, **kwargs):
#         return render(request, 'accounts/loan.html', {
#             'user': request.user
#         })

#     def post(self, request, *args, **kwargs):
#         current_time = timezone.make_aware(datetime.now())
#         if current_time >= START_TIME and current_time <= STOP_TIME:
#             mode = request.POST.get('mode')
#             user = request.user
#             if mode == 'issue':
#                 decision = user.issue_loan()
#                 if decision == 'success':
#                     messages.success(request, 'Loan issued.')
#                 elif decision == 'loan_count_exceeded':
#                     messages.error(
#                         request,
#                         'Loan can be issued only {max_issue} times in a day!'.format(max_issue=MAX_LOAN_ISSUE)
#                     )
#                 elif decision == 'bottomline_not_reached':
#                     messages.error(
#                         request,
#                         'Cash must be less than {bottom_line} to issue a loan. Your current balance: {cash}'.format(
#                             bottom_line=BOTTOMLINE_CASH,
#                             cash=user.cash
#                         )
#                     )
#                 else:
#                     messages.error(request, 'Cannot Issue loan right now.')
#             elif mode == 'pay':
#                 repay_amount = int(request.POST.get('repay_amount'))
#                 if user.loan <= 0:
#                     messages.error(request, "You have no pending loan!")
#                 elif user.loan > 0:
#                     if repay_amount <= 0 or repay_amount > user.cash:
#                         messages.error(request, 'Please enter a valid amount.')
#                     elif user.pay_installment(repay_amount):
#                         messages.success(request, 'Installment paid!')
#                     else:
#                         messages.error(
#                             request,
#                             'You should have sufficient balance!'
#                         )
#         else:
#             msg = 'The market is closed!'
#             messages.info(request, msg)

#         if request.is_ajax():
#             return JsonResponse({'next_path': reverse('account:loan')})

#         return redirect('account:loan')


# -- registration with activation begin ---


# -- registration with activation end ---

# def activate(request, uidb64, token):
#     try:
#         uid = force_text(urlsafe_base64_decode(uidb64))
#         user = User.objects.get(pk=uid)
#     except(TypeError, ValueError, OverflowError, User.DoesNotExist):
#         user = None
#     if user is not None and account_activation_token.check_token(user, token):
#         user.is_active = True
#         user.save()
#         login(request, user)
#         #return redirect('home')
#         return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
#     else:
#         return HttpResponse('Activation link is invalid!')


# class AccountEmailActivateView(FormMixin, View):
#     success_url = '/login/'
#     form_class = ReactivateEmailForm
#     key = None

#     def get(self, request, key=None, *args, **kwargs):
#         self.key = key
#         if key is not None:
#             qs = EmailActivation.objects.filter(key__iexact=key)
#             confirm_qs = qs.confirmable()
#             if confirm_qs.count() == 1:  # Not confirmed but confirmable
#                 obj = confirm_qs.first()
#                 obj.activate()
#                 messages.success(request, 'Your email has been confirmed! Please login to continue.')
#                 return redirect('login')
#             else:
#                 activated_qs = qs.filter(activated=True)
#                 if activated_qs.exists():
#                     # reset_link = reverse('password_reset')
#                     # msg = """Your email has already been confirmed.
#                     # Do you want to <a href="{link}">reset you password</a>?""".format(link=reset_link)
#                     # messages.success(request, mark_safe(msg))
#                     return redirect('login')
#         context = {'form': self.get_form(), 'key': key}  # get_form() works because of the mixin
#         return render(request, 'registration/activation_error.html', context)

#     def post(self, request, *args, **kwargs):
#         # create a form to receive an email
#         form = self.get_form()
#         if form.is_valid():
#             return self.form_valid(form)
#         else:
#             return self.form_invalid(form)

#     def form_valid(self, form):
#         msg = 'Activation link sent. Please check your email.'
#         messages.success(self.request, msg)
#         email = form.cleaned_data.get('email')
#         # obj = EmailActivation.objects.email_exists(email).first()
#         user = obj.user
#         # new_activation = EmailActivation.objects.create(user=user, email=email)
#         # new_activation.send_activation() #This function sends the activation email to the user
#         # return super(AccountEmailActivateView, self).form_valid(form)

#     def form_invalid(self, form):
#         """
#         This method had to be explicitly written because this view uses the basic django "View" class.
#         If it had used some other view like ListView etc. Django would have handled it automatically.
#         """
#         context = {'form': form, 'key': self.key}
#         return render(self.request, 'registration/activation_error.html', context)


# @login_required
# def close_bank(request):
#     """ Deduct Interest and cancel loan """
#     if request.user.is_superuser:
#         for user in get_user_model().objects.all():
#             user.cancel_loan()
#             user.deduct_interest()
#         return HttpResponse('Bank Closed', status=200)
#     return redirect('home')


# @login_required
# def cancel_loan(request):
#     """ Deduct entire loan amount from user's balance """
#     if request.user.is_superuser:
#         for user in User.objects.all():
#             user.cancel_loan()
#         return HttpResponse('Loan Deducted', status=200)
#     return redirect('home')


# @login_required
# def deduct_interest(request):
#     """ Deduct interest from user's balance """
#     if request.user.is_superuser:
#         for user in get_user_model().objects.all():
#             user.deduct_interest()
#         return HttpResponse('Interest Deducted', status=200)
#     return redirect('home')


###########################models ######################################################

# This is the email activation related code that has been commented out right now.

# class EmailActivationQuerySet(models.query.QuerySet):

#     def confirmable(self):
#         """
#         Returns those emails which can be confirmed i.e. which are not activated and expired
#         """
#         now = timezone.now()
#         start_range = now - timedelta(days=DEFAULT_ACTIVATION_DAYS)
#         end_range = now
#         return self.filter(activated=False, forced_expire=False).filter(
#             timestamp__gt=start_range, timestamp__lte=end_range
#         )


# class EmailActivationManager(models.Manager):

#     def get_queryset(self):
#         return EmailActivationQuerySet(self.model, using=self._db)

#     def confirmable(self):
#         return self.get_queryset().confirmable()

#     def email_exists(self, email):
#         """
#         EmailActivation is created when the user is created. When only EmailActivation is deleted, User object
#         still remains i.e. email still exists. But this function will send nothing because for this function
#         self.get_queryset() is None. So both user and EmailActivation should exist together for this to work.
#         """
#         return self.get_queryset().filter(
#             Q(email=email) | Q(user__email=email)
#         ).filter(activated=False)


# class EmailActivation(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     email = models.EmailField()
#     key = models.CharField(max_length=120, blank=True, null=True)  # activation key
#     activated = models.BooleanField(default=False)
#     forced_expire = models.BooleanField(default=False)  # link expired manually
#     expires = models.IntegerField(default=7)  # automatic expire (after days)
#     timestamp = models.DateTimeField(auto_now_add=True)
#     update = models.DateTimeField(auto_now=True)

#     objects = EmailActivationManager()

#     def __str__(self):
#         return self.email

#     def can_activate(self):
#         qs = EmailActivation.objects.filter(pk=self.pk).confirmable()
#         if qs.exists():
#             return True
#         return False

#     def activate(self):
#         if self.can_activate():
#             user = self.user
#             user.is_active = True
#             user.save()
#             self.activated = True
#             self.save()
#             return True
#         return False

#     def send_activation(self): # This function sends the activation email to the user.
#         # Twilio phone number: +12035775609
#         # account_sid: AC638c5918088e09c2e0a2133bb4b91176
#         # auth_token: 32c25449fae648690e91828902e27096
#         if not self.activated and not self.forced_expire:
#             if self.key:
#                 base_url = getattr(settings, 'HOST_SCHEME') + getattr(settings, 'BASE_URL')
#                 key_path = reverse('account:email-activate', kwargs={'key': self.key})
#                 path = '{base}{path}'.format(base=base_url, path=key_path)
#                 context = {
#                     'path': path,
#                     'email': self.email
#                 }
#                 txt_ = get_template('registration/emails/verify.txt').render(context)
#                 html_ = get_template('registration/emails/verify.html').render(context) #get_template('activation_email.html').render(context) #
#                 subject = 'Cricket Stock Exchange - Verify your account' #'Morphosis Stock Bridge - Verify your Account'
#                 from_email = settings.DEFAULT_FROM_EMAIL
#                 recipient_list = [self.email]
#                 sent_mail = send_mail(
#                     subject,
#                     txt_,  # If content_type is text/plain
#                     from_email,
#                     recipient_list,
#                     html_message=html_,  # If content_type is text/html
#                     fail_silently=False  # If false, then an email will be sent if error occurs while sending the email
#                 )
#                 return sent_mail
#         return False


# def pre_save_email_activation_receiver(sender, instance, *args, **kwargs):
#     if not instance.activated and not instance.forced_expire and not instance.key:
#         instance.key = unique_key_generator(instance)


# pre_save.connect(pre_save_email_activation_receiver, sender=EmailActivation)


# def post_save_user_create_receiver(sender, instance, created, *args, **kwargs):
#     if created:
#         email_obj = EmailActivation.objects.create(user=instance, email=instance.email)
#         email_obj.send_activation()


# post_save.connect(post_save_user_create_receiver, sender=User)
