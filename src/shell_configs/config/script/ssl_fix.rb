# frozen_string_literal: true

# Corporate SSL Fix for Ruby
#
# Fixes "certificate verify failed (unable to get certificate CRL)" errors
# caused by corporate CA certificates requiring CRL checking.
#
# ROOT CAUSE:
#   Corporate SSL inspection adds CA certs to the system keychain that require
#   CRL (Certificate Revocation List) verification. Ruby's Net::HTTP default
#   SSL setup uses the system keychain, which includes these corporate CAs.
#   The CRL endpoints are typically internal URLs that Ruby/OpenSSL can't reach.
#
# THE FIX:
#   Patches Net::HTTP to use an explicit OpenSSL cert store with set_default_paths,
#   which uses Homebrew's CA bundle (/opt/homebrew/etc/ca-certificates/cert.pem)
#   instead of the system keychain, avoiding the corporate CA chain entirely.
#
# USAGE:
#   Option 1 - Via shell-configs wrapper functions (recommended):
#     rubyssl your_script.rb
#     bundlessl exec rake task
#
#   Option 2 - Direct with environment variable (if $SHELL_CONFIGS_DIR is set):
#     RUBYOPT="-r $SHELL_CONFIGS_DIR/script/ssl_fix.rb" ruby script.rb
#     RUBYOPT="-r $SHELL_CONFIGS_DIR/script/ssl_fix.rb" bundle exec ruby script.rb
#
#   Option 3 - Require in script (if you know the absolute path):
#     require '/path/to/shell_configs/config/script/ssl_fix.rb'
#

require 'openssl'
require 'net/http'

module CorporateSSLFix
  VERSION = "1.0.0"

  def self.applied?
    @applied ||= false
  end

  def self.apply!
    return if applied?

    Net::HTTP.prepend(NetHTTPPatch)
    @applied = true

    warn "[ssl_fix] Corporate SSL fix applied"
    warn "[ssl_fix] Using: #{OpenSSL::X509::DEFAULT_CERT_FILE}"
  end

  module NetHTTPPatch
    def connect
      # Only apply fix if:
      # 1. No custom cert_store was set (respect user overrides)
      # 2. SSL is enabled
      if @cert_store.nil? && use_ssl?
        @cert_store = OpenSSL::X509::Store.new
        @cert_store.set_default_paths
      end
      super
    end
  end
end

# Auto-apply when required
CorporateSSLFix.apply!
