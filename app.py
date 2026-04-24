st.markdown("---")
        st.markdown(
            "<div style='font-size:0.85rem;color:#7a8299;margin-bottom:4px;'>"
            "Type <b style='color:#4f9cf9;'>SAVE</b> in the box below to confirm and activate the Save button.</div>",
            unsafe_allow_html=True
        )
        confirm_text = st.text_input(
            "Type SAVE to confirm",
            key=f"vf_confirm_text_{bin_id}",
            placeholder="Type SAVE here…",
            label_visibility="collapsed"
        )
        confirmed = confirm_text.strip().upper() == "SAVE"

        cs, cc = st.columns(2)
        with cs:
            submitted = st.form_submit_button(
                "💾  Save Material", type="primary",
                use_container_width=True)
        with cc:
            cancelled = st.form_submit_button("✕  Cancel", use_container_width=True)

        if submitted:
            if not confirmed:
                st.error("⚠️  Please type SAVE in the confirmation box to proceed.")
            else:
                new_vals["_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data[bin_id] = new_vals
                save_data(data)
                st.session_state.pop(f"v_mode_{bin_id}", None)
                st.session_state.pop(f"auth_ok_{bin_id}", None)
                st.success(f"✅ Bin {bin_id} saved successfully!")
                st.rerun()
        if cancelled:
            st.session_state.pop(f"v_mode_{bin_id}", None)
            st.session_state.pop(f"auth_ok_{bin_id}", None)
            st.rerun()
