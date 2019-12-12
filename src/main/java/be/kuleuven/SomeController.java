package be.kuleuven;

import javafx.event.ActionEvent;
import javafx.fxml.FXML;
import javafx.scene.control.Button;
import javafx.scene.control.TextField;

public class SomeController {

    @FXML
    private Button button;

    @FXML
    private TextField text;

    public void initialize() {
        button.setOnAction(e -> clickedOnButton(e));
    }

    private void clickedOnButton(ActionEvent e) {
        text.setText("You clicked! Wowza");
    }
}
