
function! denite_autocmd#util#redir(cmd) abort
    let [tmp_verbose, tmp_verbosefile] = [&verbose, &verbosefile]
    set verbose=0 verbosefile=
    redir => result
    silent! execute a:cmd
    redir END
    let [&verbose, &verbosefile] = [tmp_verbose, tmp_verbosefile]
    return result
endfunction

